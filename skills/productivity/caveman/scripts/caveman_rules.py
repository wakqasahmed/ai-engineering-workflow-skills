"""Shared caveman compression and lint vocabulary."""


FILLER_WORDS = (
    "just",
    "really",
    "basically",
    "actual",
    "actually",
    "simply",
    "obviously",
    "literally",
)

HEDGING_WORDS = ("might", "maybe", "perhaps", "likely", "possibly", "probably")

PLEASANTRY_PHRASES = (
    "sure",
    "certainly",
    "of course",
    "happy to help",
    "i'd be happy to",
    "i would be happy to",
    "great question",
    "good question",
    "absolutely",
    "no problem",
)

METATALK_PHRASES = (
    "as you can see",
    "it should be noted",
    "it's worth mentioning",
    "it is worth mentioning",
    "worth mentioning",
    "needless to say",
    "to be clear",
    "in other words",
    "that said",
    "having said that",
)

SINGLE_QUOTED_LITERAL_PATTERN = (
    r"(?<!\w)'(?!\d{2}s\b)(?:\\.|[^'\\.!?…\n]){0,120}'"
)
