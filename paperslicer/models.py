from __future__ import annotations
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Any


@dataclass
class Meta:
    source_path: str
    title: Optional[str] = None
    journal: Optional[str] = None
    doi: Optional[str] = None
    authors: List[Dict[str, Optional[str]]] = field(default_factory=list)
    keywords: List[str] = field(default_factory=list)


@dataclass
class PaperRecord:
    meta: Meta
    sections: Dict[str, str] = field(default_factory=dict)
    other_sections: Dict[str, str] = field(default_factory=dict)
    figures: List[Dict[str, Any]] = field(default_factory=list)
    tables: List[Dict[str, Any]] = field(default_factory=list)
    references: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "meta": asdict(self.meta),
            "sections": self.sections,
            "other_sections": self.other_sections,
            "figures": self.figures,
            "tables": self.tables,
            "references": self.references,
        }
