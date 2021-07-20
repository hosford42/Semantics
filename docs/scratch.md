```
Sentence: "One is a number."

Structure: One <SUBJECT is OBJECT> (a <DETERMINER number).

Let <NOW> df.= INSTANCE[kind=KIND[name=WORD[name="time"]],
                        name=WORD[name="now"]]

EVENT[kind=KIND[NAME=WORD[name="be"]],
      subject=INSTANCE[name=WORD[name="one"]],
      object=INSTANCE[kind=KIND[name=WORD[name="number"]],
                      selector=SELECTOR[name=WORD[name="a"]]],
      time=TIME[includes=<NOW>]]
```

Note that no duration is specified for the event's time. Only with the
additional knowledge that numbers do not generally change can it be
inferred that, "One is always a number."
