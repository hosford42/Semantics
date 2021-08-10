# See:
#   * https://github.com/bokeh/bokeh/blob/2.3.3/examples/howto/server_embed/standalone_embed.py
#   * https://docs.bokeh.org/en/latest/docs/user_guide/graph.html#userguide-graph
#   * http://holoviews.org/getting_started/Live_Data.html
#   * http://holoviews.org/user_guide/Deploying_Bokeh_Apps.html
#   * http://holoviews.org/user_guide/Network_Graphs.html
#   * https://docs.bokeh.org/en/latest/docs/user_guide/interaction/callbacks.html#openurl
#   * https://panel.holoviz.org/user_guide/Param.html
#   * http://holoviews.org/user_guide/Plotting_with_Bokeh.html
#   * https://github.com/holoviz/holoviews/issues/3562
#   * http://holoviews.org/user_guide/Styling_Plots.html

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
import json
import logging
import math
import random
import warnings
from contextlib import contextmanager
from functools import reduce
from itertools import chain
from typing import Tuple, List, Mapping, Iterable, Optional, Any, Union

import holoviews as hv
import numpy as np
import panel as pn
import param
from bokeh.models import HoverTool, CustomJS
from holoviews.streams import SingleTap
from panel.io.server import StoppableThread

from semantics.data_types.indices import VertexID
from semantics.data_types.language_ids import LanguageID
from semantics.graph_layer.interface import GraphDBInterface
from semantics.kb_layer.interface import KnowledgeBaseInterface
from semantics.kb_layer.knowledge_base import KnowledgeBase

LOGGER = logging.getLogger(__name__)

hv.extension('bokeh')


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


def get_vertex_roles(db: GraphDBInterface, vertices: Iterable[VertexID]) -> Mapping[VertexID, str]:
    return {vid: db.get_vertex(vid).preferred_role.name for vid in vertices}


def get_vertex_color_indices(db: GraphDBInterface,
                             vertices: Iterable[VertexID]) -> Mapping[VertexID, int]:
    return {vid: int(db.get_vertex(vid).preferred_role.index)
            for vid in vertices}


def arrange_neighborhood(db: GraphDBInterface,
                         vertices: Iterable[VertexID],
                         margin: float = 0.05) -> Mapping[VertexID, Tuple[float, float]]:
    assert margin > 0
    vertices = list(vertices)
    layers = []
    remainder = list(vertices)
    covered = set()
    while remainder:
        layer = set(remainder)
        sources = {
            v: set(e.source.index for e in db.get_vertex(v).iter_inbound())
            for v in layer
        }
        sinks = {
            v: set(e.sink.index for e in db.get_vertex(v).iter_outbound())
            for v in layer
        }
        same_level_neighbors = {
            v: (sources[v] | sinks[v]) & layer
            for v in layer
        }
        same_level_counts = {
            v: len(same_level_neighbors[v])
            for v in layer
        }
        previous_level_counts = {
            v: (sum(e.source.index in covered for e in db.get_vertex(v).iter_inbound()) +
                sum(e.sink.index in covered for e in db.get_vertex(v).iter_outbound()))
            for v in layer
        }
        layer = sorted(layer, key=lambda v: (db.get_vertex(v).count_inbound() > 0,
                                             same_level_counts[v] - previous_level_counts[v]))
        kept = []
        remainder = None
        previous_inbound_count = None
        for index, v in enumerate(layer):
            inbound_count = db.get_vertex(v).count_inbound()
            if previous_inbound_count is None:
                previous_inbound_count = inbound_count
            if set(kept) & same_level_neighbors[v] or inbound_count > previous_inbound_count:
                remainder = layer[index:]
                break
            kept.append(v)
        assert kept
        layers.append(kept)
        covered.update(kept)

    spaced_layers = [[] for _ in layers]
    counts = [0 for _ in layers]
    fraction_complete: List[float] = [0.5 / len(layer) for layer in layers]
    vertex_index_map = {}
    while any(count < len(layer) for count, layer in zip(counts, layers)):
        assert all(0 <= fraction <= 1 for fraction in fraction_complete)
        selected_layer = min(range(len(layers)), key=fraction_complete.__getitem__)
        assert isinstance(selected_layer, int)
        assert counts[selected_layer] < len(layers[selected_layer])
        vertex_id = layers[selected_layer][counts[selected_layer]]
        # TODO: While adding this column would cause a newly placed edge to coincide with a
        #       previously placed vertex, add an empty column. We can tell if a newly placed edge
        #       would intersect with a previously placed vertex by identifying the other end of the
        #       edge and then walking step by step through the layers at the slope of the edge.
        vertex = db.get_vertex(vertex_id)
        while True:
            for layer in spaced_layers:
                layer.append(None)
            intersection_detected = False
            for edge in chain(vertex.iter_inbound(), vertex.iter_outbound()):
                if edge.source == vertex:
                    other_vertex = edge.sink
                else:
                    other_vertex = edge.source
                if other_vertex.index not in vertex_index_map:
                    continue
                other_y, other_x = vertex_index_map[other_vertex.index]
                if other_y is None or other_x is None:
                    continue
                for x in range(other_x + 1, len(spaced_layers[selected_layer])):
                    x_ratio = (x - other_x) / (len(spaced_layers[selected_layer]) - other_x - 1)
                    y = other_y + (selected_layer - other_y) * x_ratio
                    if abs(y - round(y)) > 0.25:
                        continue
                    y = round(y)
                    if y < len(spaced_layers) and spaced_layers[y][x] is not None:
                        intersection_detected = True
                        break
            if not intersection_detected:
                break
        spaced_layers[selected_layer][-1] = vertex_id
        counts[selected_layer] += 1
        fraction_complete[selected_layer] += 1 / (len(layers[selected_layer]) + 1)
        vertex_index_map[vertex_id] = selected_layer, len(spaced_layers[selected_layer]) - 1

    previous_layer_lengths = set()
    positions = {}
    for y_index, layer in enumerate(spaced_layers):
        # y = (y_index + margin) / (len(layers) - 1 + 2 * margin)
        # assert 0 < y < 1
        # y = 2 * (y_index - (len(layers) - 1) * 0.5) / max(len(layers) - 1, 1)
        y = (2 * y_index + 0.5) / len(layers) - 1
        # if len(layer) % 2:
        #     layer.append(None)
        # while any(math.gcd(len(layer) + 1, p) != 1 for p in previous_layer_lengths):
        for x_index, v in enumerate(layer):
            # x = (x_index + margin) / (len(layer) - 1 + 2 * margin)
            # assert 0 < x < 1
            if v is None:
                continue
            # x = 2 * (x_index - (len(layer) - 1) * 0.5) / max(len(layer) - 1, 1)
            x = (2 * x_index + 0.5) / len(layer) - 1
            positions[v] = (x, y)
            print(v, (x, y))
        previous_layer_lengths.add(len(layer) // 2 * 2 + 1)
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


def get_node_data(db: GraphDBInterface, vertices: Iterable[VertexID]) \
        -> Tuple[Tuple[str, ...], Tuple[List[Any], ...]]:
    vertices = list(vertices)
    vertex_roles = get_vertex_roles(db, vertices)
    vertex_positions = arrange_neighborhood(db, vertices)

    x = [vertex_positions[vid][0] for vid in vertices]
    y = [vertex_positions[vid][1] for vid in vertices]
    role = [vertex_roles[vid] for vid in vertices]

    data = {}
    keys = set()
    for vertex_id in vertices:
        vertex = db.get_vertex(vertex_id)
        vertex_data = {}
        for key in vertex.iter_data_keys():
            value = vertex.get_data_key(key)
            vertex_data[key] = value
            keys.add(key)
        data[vertex_id] = vertex_data
    keys = tuple(sorted(keys))
    values = []
    for key in keys:
        value_list = []
        for vertex_id in vertices:
            value = data[vertex_id].get(key, None)
            if isinstance(value, LanguageID):
                value = str(value)
            assert value is None or isinstance(value, (int, float, str))
            if value is None:
                value = ''
            value_list.append(value)
        values.append(value_list)
    values = tuple(values)

    return ('x', 'y', 'index', 'Role') + keys, (x, y, vertices, role) + values


class Explorer(param.Parameterized):
    vid = param.Integer(default=0)
    vid_str = param.String(default='0')

    def __init__(self, kb: KnowledgeBaseInterface, **params):
        super().__init__(**params)
        self.vid_input = pn.widgets.TextInput(name='Vertex ID', value=self.vid_str)
        self._kb = kb
        self._node_radius = 0.05
        self._positions = None
        self._graph = None
        self._update_graph()

        def callback(target, event):
            target.vid_str = event.new

        self.vid_input.link(self, callbacks={'value': callback})

    def _update_graph(self):
        db = self._kb.database
        vertices = get_neighborhood(db, VertexID(self.vid))
        vertex_positions = arrange_neighborhood(db, vertices)
        edges = get_edges(db, vertices)

        node_data_names, node_data = get_node_data(db, vertices)
        assert node_data_names[:3] == ('x', 'y', 'index')
        nodes = hv.Nodes(node_data, vdims=list(node_data_names[3:]))
        node_labels = hv.Labels(nodes, ['x', 'y'], 'index')

        source = [edge[1] for edge in edges]
        sink = [edge[2] for edge in edges]

        graph = hv.Graph(((source, sink), nodes))

        label = [edge[0] for edge in edges]
        x = [(vertex_positions[edge[1]][0] + vertex_positions[edge[2]][0]) / 2
             for edge in edges]
        y = [(vertex_positions[edge[1]][1] + vertex_positions[edge[2]][1]) / 2
             for edge in edges]
        rise = [vertex_positions[edge[2]][1] - vertex_positions[edge[1]][1] for edge in edges]
        run = [vertex_positions[edge[2]][0] - vertex_positions[edge[1]][0] for edge in edges]
        angle = [(math.atan2(y_delta, x_delta) * 360 / math.tau + 90) % 180 - 90
                 for y_delta, x_delta in zip(rise, run)]
        edge_label_points = hv.Dataset((x, y, label, angle), kdims=['x', 'y', 'Label'],
                                       vdims='angle')

        edge_labels = hv.Labels(edge_label_points, ['x', 'y'], ['Label', 'angle']).opts(
            angle='angle'
        )

        self._positions = vertex_positions
        self._graph = graph.opts(
            directed=True,
            arrowhead_length=self._node_radius,
            node_color='Role',
            node_radius=self._node_radius,
            cmap='glasbey_hv',
            width=900,
            height=800,
            xaxis=None,
            yaxis=None,
            aspect='equal',  # This is necessary for arrow heads to be rendered properly
            # responsive=True
        ) * node_labels.opts(
            text_font_size='8pt',
            text_color='white',
            bgcolor='gray',
        ) * edge_labels.opts(
            text_font_size='8pt',
            text_color='white',
            bgcolor='gray'
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
        # This is maybe a slight abuse of DynamicMap.
        return hv.DynamicMap(self._intercept_clicks, streams=[SingleTap()])

    def panel(self):
        return pn.Column(self.view, self.vid_input)


def explore(kb: KnowledgeBaseInterface, background: bool = False) -> Optional[StoppableThread]:
    """Explore the knowledge base via the browser. If background is False
    (default), run in a foreground thread and return None when the user hits
    Ctrl-C. If background is True, run in a background thread and return the
    thread; the caller will have to call `thread.stop()` before the program is
    exited, or else the user will have to hit Ctrl-C to end the program."""
    try:
        server = pn.serve(Explorer(kb).panel(), threaded=background)
    except KeyboardInterrupt:
        return None
    else:
        assert background
        return server


@contextmanager
def exploring(kb: KnowledgeBaseInterface):
    thread = explore(kb, background=True)
    try:
        yield
    finally:
        thread.stop()


def manual_test():
    kb = KnowledgeBase()
    explore(kb)


if __name__ == '__main__':
    manual_test()
