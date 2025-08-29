from dataclasses import dataclass
from typing import Any, Dict, List, Optional


@dataclass
class Meta:
    source_path: str
    title: Optional[str] = None


@dataclass
class PaperRecord:
    meta: Meta
    sections: Dict[str, str]
    figures: Optional[List[Dict[str, Any]]] = None
    tables: Optional[List[Dict[str, Any]]] = None
