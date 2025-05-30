# cm-events

Simple async pub/sub package I made for an assignment of an Embedded Systems curricular unit.

## What it does
Just decouples pub/sub messaging from actual business logic like reading sensors and pushing notifications. 
Didn't like all the bloated code I had so I built this mini package to abstract away event handling 
using decorators and implementing just the required methods for an RPI controller needed for the assignment.

Basically, It lets you:

- Have components that publish events (like sensor readers)
- Have components that subscribe to events (like data processors)
- Auto-register components with decorators
- Basic state machine support for stateful components

## Basic usage

```python
from events import EventType, Event, Publisher, Subscriber, Broker, register

class YourEvents(EventType):
    SOME_EVENT = "some_event"

@register
class YourSensor(Publisher):
    
    async def startup(self):
       ... # start up your sensor
    
    async def run(self):
        while True:
            reading = sense()  # your sensor code
            await self.publish(Event(
                type=YourEvents.SOME_EVENT,
                source="sensor_1",
                payload={"value": reading}
            ))
            await asyncio.sleep(1)
        
    async def shutdown(self):
        ... # shutdown your sensor

@register  
class ReadingLogger(Subscriber):
    
    async def startup(self):
        self.subscribe_to(YourEvents.SOME_EVENT)
    
    async def handle_event(self, event):
        print(f"Reading: {event.payload['value']}")

# Run it
async def main():
    broker = Broker()
    await broker.start()
    
    try:
        while True:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        pass
    
    await broker.stop()

asyncio.run(main())
```

## Component types

- `Publisher` - broadcasts events via `publish()`
- `Subscriber` - receives subscribed events via `handle_event()`  
- `Transceiver` - does both

## Multiple instances

If you need multiple instances of the same component:

```python
from events import Publisher, register_multiple

@register_multiple([
    {"pin": 18, "name": "sensor1"},
    {"pin": 19, "name": "sensor2"}
])
class GPIOSensor(Publisher):
    def __init__(self, pin, name):
        self._pin = pin
        self._name = name

    # ...
```

## State machines

For components that need states:

```python
from events import StateMachine, Publisher, register, state, initial_state

@register
@initial_state("idle")
class StatefulComponent(StateMachine, Publisher):
    
    @state("idle", poll_interval=1.0)
    async def idle_state(self):
        if some_condition():
            return "working"
    
    @state("working", poll_interval=0.1) 
    async def working_state(self):
        do_work()
        if done():
            return "idle"
```

## Install

```bash
poetry add cm-events
```

Requires Python 3.11+ and pydantic.
