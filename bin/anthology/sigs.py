# Marcel Bollmann <marcel@bollmann.me>, 2019

from collections import defaultdict, namedtuple
from slugify import slugify
import logging as log
import yaml
from .data import SIG_FILES
from .papers import to_volume_id

try:
    from yaml import CLoader as Loader
except ImportError:
    from yaml import Loader


SIGEvent = namedtuple(
    "SIGEvent",
    ["anthology_id", "name", "url", "year"],
    defaults=[None, None, None, None],
)


def _sigevent_to_repr(event):
    if event.anthology_id is not None:
        # For some reason, SIG files point to the front matter, not to the
        # containing proceedings volume -- change that here
        return to_volume_id(event.anthology_id)
    return {"name": event.name, "url": event.url}


class SIGIndex:
    def __init__(self, srcdir=None):
        self.sigs = {}
        if srcdir is not None:
            self.load_from_dir(srcdir)

    def load_from_dir(self, directory):
        for filename in SIG_FILES:
            log.debug("Instantiating SIG from {}...".format(filename))
            with open("{}/{}".format(directory, filename), "r") as f:
                data = yaml.load(f, Loader=Loader)
                sig = SIG.from_dict(data)
                self.sigs[sig.acronym] = sig

    def get_associated_sigs(self, anthology_id):
        return [
            acronym
            for acronym, sig in self.sigs.items()
            if sig.is_associated_with(anthology_id)
        ]

    def items(self):
        return self.sigs.items()


class SIG:
    def __init__(self, acronym, name, url):
        self.acronym = acronym
        self.name = name
        self.url = url
        self._data = {}
        self._associated_events = []
        self.events_by_year = {}

    def from_dict(dict_):
        sig = SIG(dict_["ShortName"], dict_["Name"], dict_.get("URL", None))
        sig.data = dict_
        return sig

    @property
    def associated_events(self):
        return self._associated_events

    @property
    def data(self):
        return self._data

    @data.setter
    def data(self, dict_):
        self._data = dict_
        self._associated_events = []
        self.events_by_year = defaultdict(list)
        for eventdicts in dict_["Meetings"]:
            for year, events in eventdicts.items():
                for event in events:
                    if isinstance(event, str):
                        ev = SIGEvent(anthology_id=event, year=year)
                    elif isinstance(event, dict):
                        ev = SIGEvent(
                            name=event["Name"], url=event.get("URL", None), year=year
                        )
                    else:
                        log.warning(
                            "In SIG '{}': Unknown event format: {}".format(
                                self.acronym, type(event)
                            )
                        )
                    self._associated_events.append(ev)
                    self.events_by_year[year].append(ev)

    @property
    def slug(self):
        return slugify(self.acronym)

    @property
    def volumes_by_year(self):
        return {
            y: [_sigevent_to_repr(e) for e in k] for y, k in self.events_by_year.items()
        }

    @property
    def years(self):
        return self.events_by_year.keys()

    def is_associated_with(self, anthology_id):
        return any(ev.anthology_id == anthology_id for ev in self._associated_events)
