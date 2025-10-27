"""
Chunking tekstualnih dokumenata sa overlap strategijom.
"""
import re
from typing import List


def chunk(text: str, max_len: int = 1200, overlap: int = 150) -> List[str]:
    """
    Podela teksta na segmente sa overlap.
    
    Args:
        text: Input tekst
        max_len: Maksimalna dužina segmenta
        overlap: Dužina overlap-a između segmenata
        
    Returns:
        Lista segmenata
    """
    # Grubo deljenje po rečenicama
    sentences = re.split(r'(?<=[\.\!\?])\s+', text.strip())
    
    buf = []
    cur = 0
    
    for s in sentences:
        if cur + len(s) > max_len and buf:
            # Emituj segment
            yield " ".join(buf)
            
            # Overlap: poslednjih ~overlap karaktera
            tail = (" ".join(buf))[-overlap:]
            buf = [tail, s]
            cur = len(tail) + len(s)
        else:
            buf.append(s)
            cur += len(s)
    
    # Poslednji segment
    if buf:
        yield " ".join(buf)

