# See:
#   * https://github.com/bokeh/bokeh/blob/2.3.3/examples/howto/server_embed/standalone_embed.py
#   * https://docs.bokeh.org/en/latest/docs/user_guide/graph.html#userguide-graph
#   * http://holoviews.org/getting_started/Live_Data.html
#   * http://holoviews.org/user_guide/Deploying_Bokeh_Apps.html
#   * http://holoviews.org/user_guide/Network_Graphs.html
#   * https://docs.bokeh.org/en/latest/docs/user_guide/interaction/callbacks.html#openurl
#   * https://panel.holoviz.org/user_guide/Param.html

# Design requirements:
#   * Absolute navigation: Type in any vertex ID to center it. Type in a word to center the
#     corresponding word vertex.
#   * Relative navigation: Click on a displayed vertex to center it.
#   * History navigation: Use backward and forward arrows to move back and forth through recently
#     visited vertices.
#   * Neighborhood of centered vertex are shown out to a fixed depth, radiating from the centered
#     vertex.
#   * Displayed neighborhood depth is dynamically configurable.
#   * The image zoom is increased or decreased to fit the graph within the window. (If it's not
#     possible to determine window size to fit to it, allow user to control zoom and use
#     proportionate zoom increases/decreases.)
#   * Edges between displayed vertices are displayed.
#   * Edges are displayed with arrows to indicate direction.
#   * Vertices are labeled with their role names and IDs.
#   * Edges are labeled with their label names.
#   * Hovering over a vertex or edge causes comprehensive data to be displayed for that
#     element, including data keys/values.
#   * Edges are never directly overlapping -- they can be parallel or intersect, but not both.
#   * Vertices are sorted vertically in the display to maximize the number of edges whose sources
#     appear above their sinks.
#   * Within the previous constraints, vertices are sorted horizontally to maximize the number of
#     edges whose sources are at or below their sinks and whose sources appear to the left of their
#     sinks. (In other words, if we can't perfectly sort them vertically, try to sort them
#     horizontally.)
#   * Within the previous constraints, edge intersections are minimized.
#   * Within the previous constraints, edges should not cross vertices.
#   * When edges must cross vertices, vertices should appear on top.
#   * The current view can be saved as an image.


import logging
import math
from typing import Tuple, List, Mapping, Iterable

import holoviews as hv
import panel as pn
import param
from holoviews.streams import SingleTap

from semantics.data_types.indices import VertexID
from semantics.graph_layer.interface import GraphDBInterface
from semantics.kb_layer.interface import KnowledgeBaseInterface
from semantics.kb_layer.knowledge_base import KnowledgeBase

LOGGER = logging.getLogger(__name__)


def get_neighborhood(db: GraphDBInterface, vertex_id: VertexID, depth: int = 1) -> List[VertexID]:
    neighborhood = {vertex_id}
    new_additions = {vertex_id}
    for _ in range(depth):
        new_sources = {edge.source.index
                       for vid in new_additions
                       for edge in db.get_vertex(vid).iter_inbound()}
        new_sinks = {edge.sink.index
                     for vid in new_additions
                     for edge in db.get_vertex(vid).iter_outbound()}
        new_additions = (new_sources | new_sinks) - neighborhood
        if not new_additions:
            break
        neighborhood.update(new_additions)
    return sorted(neighborhood)


def get_vertex_labels(db: GraphDBInterface, vertices: Iterable[VertexID]) -> Mapping[VertexID, str]:
    return {vid: '%s#%s' % (db.get_vertex(vid).preferred_role.name, int(vid))
            for vid in vertices}


def get_vertex_color_indices(db: GraphDBInterface,
                             vertices: Iterable[VertexID]) -> Mapping[VertexID, int]:
    return {vid: int(db.get_vertex(vid).preferred_role.index)
            for vid in vertices}


def arrange_neighborhood(db: GraphDBInterface,
                         vertices: Iterable[VertexID]) -> Mapping[VertexID, Tuple[float, float]]:
    inbound_counts = {
        v: sum(edge.source.index in vertices for edge in db.get_vertex(v).iter_inbound())
        for v in vertices
    }
    outbound_counts = {
        v: sum(edge.sink.index in vertices for edge in db.get_vertex(v).iter_outbound())
        for v in vertices
    }
    positions = {}
    max_y = len(inbound_counts)
    for y, count in enumerate(sorted(inbound_counts.values())):
        y_relative = 2.0 * y / max_y - 1.0
        layer = [v for v, c in inbound_counts.items() if c == count]
        layer.sort(key=outbound_counts.get)
        max_x = len(layer)
        for x, v in enumerate(layer):
            x_relative = 2.0 * x / max_x - 1.0
            positions[v] = (x_relative, -y_relative)  # Invert y axis
    return positions


def get_edges(db: GraphDBInterface,
              vertices: Iterable[VertexID]) -> List[Tuple[str, VertexID, VertexID]]:
    edges = []
    for vid in vertices:
        vertex = db.get_vertex(vid)
        for edge in vertex.iter_outbound():
            if edge.sink.index in vertices:
                edges.append((edge.label.name, vid, edge.sink.index))
    return edges


class Explorer(param.Parameterized):
    vid = param.Integer(default=0)
    vid_str = param.String(default='0')

    def __init__(self, kb: KnowledgeBaseInterface, **params):
        super().__init__(**params)
        self.vid_input = pn.widgets.TextInput(name='Vertex ID', value=self.vid_str)
        self._kb = kb
        self._node_radius = 0.08
        self._positions = None
        self._graph = None
        self._update_graph()

        def callback(target, event):
            target.vid_str = event.new

        self.vid_input.link(self, callbacks={'value': callback})

    def _update_graph(self):
        db = self._kb.database
        vertices = get_neighborhood(db, VertexID(self.vid))
        vertex_labels = get_vertex_labels(db, vertices)
        vertex_positions = arrange_neighborhood(db, vertices)
        edges = get_edges(db, vertices)

        x = [vertex_positions[vid][0] for vid in vertices]
        y = [vertex_positions[vid][1] for vid in vertices]
        label = [vertex_labels[vid] for vid in vertices]
        nodes = hv.Nodes((x, y, vertices, label), vdims='Role')
        node_labels = hv.Labels(nodes, ['x', 'y'], 'Role')

        source = [edge[1] for edge in edges]
        sink = [edge[2] for edge in edges]
        label = [edge[0] for edge in edges]

        self._positions = vertex_positions
        self._graph = hv.Graph(((source, sink, label), nodes), vdims='Label').opts(
            directed=True,
            arrowhead_length=1.5 * self._node_radius,
            node_color='Role',
            node_radius=self._node_radius,
            cmap='glasbey_hv',
            width=900,
            height=800,
            xaxis=None,
            yaxis=None,
        ) * node_labels.opts(
            text_font_size='8pt',
            text_color='white',
            bgcolor='gray',
        )

    def _intercept_clicks(self, x=None, y=None):
        assert self._graph is not None
        assert self._positions is not None
        if x is None or y is None:
            return self._graph
        selected_vid = self.vid
        for vid, (vx, vy) in self._positions.items():
            distance = math.hypot(vx - x, vy - y)
            if distance < self._node_radius:
                selected_vid = vid
                break
        self.vid = selected_vid
        self.vid_input.value = str(int(selected_vid))
        self._update_graph()
        return self._graph

    @param.depends('vid_str', watch=True)
    def _update_vid(self):
        try:
            vid = int(self.vid_str)
        except ValueError:
            return
        try:
            self._kb.database.get_vertex(VertexID(vid))
        except KeyError:
            return
        self.vid = vid

    @param.depends('vid')
    def view(self):
        LOGGER.info("Viewing VertexID(%s) in graph explorer", self.vid)
        self.vid_str = str(self.vid)
        self._update_graph()
        return hv.DynamicMap(self._intercept_clicks, streams=[SingleTap()])

    def panel(self):
        return pn.Column(self.view, self.vid_input)


if __name__ == '__main__':
    hv.extension('bokeh', 'matplotlib')
    kb = KnowledgeBase()
    pn.serve(Explorer(kb).panel(), threaded=True)
