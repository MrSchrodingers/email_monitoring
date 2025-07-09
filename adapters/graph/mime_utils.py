from __future__ import annotations
import re
from email import message_from_string, policy
from email.utils import parsedate_to_datetime
from typing import Dict, Optional

_RX_INT   = re.compile(r'-?\d+')
_IP_RE    = re.compile(r'\[?([0-9a-f:.]+)\]?')
_DKIM_RE  = re.compile(r'dkim=(pass|fail)',  re.I)
_SPF_RE   = re.compile(r'spf=(pass|fail)',   re.I)
_DMARC_RE = re.compile(r'dmarc=(pass|fail)', re.I)

def _header(msg, name: str) -> str:
    return msg.get(name, '')

def parse_mime_headers(raw: str) -> Dict[str, Optional[object]]:
    msg = message_from_string(raw, policy=policy.default)

    # --- SCL ---
    scl_hdr = _header(msg, 'X-MS-Exchange-Organization-SCL').strip()
    _scl = int(scl_hdr) if _RX_INT.fullmatch(scl_hdr) else None

    # --- Auth results ---
    auth_src = (
        _header(msg, 'Authentication-Results') +
        _header(msg, 'ARC-Authentication-Results') +
        _header(msg, 'Received-SPF')
    ).lower()

    def _pass(regex):        # helper
        m = regex.search(auth_src)
        return True if m and m.group(1) == 'pass' else (False if m else None)

    _dkim_pass  = _pass(_DKIM_RE)
    _spf_pass   = _pass(_SPF_RE)
    _dmarc_pass = _pass(_DMARC_RE)

    # --- IPs ---
    recvs = msg.get_all('Received', [])
    from_ip = to_ip = None
    if recvs:
        ips_last = _IP_RE.findall(recvs[-1])
        ips_first = _IP_RE.findall(recvs[0])
        if ips_last:
            from_ip = ips_last[-1]
        if ips_first:
            to_ip = ips_first[0]

    # --- Latência ---
    _latency = None
    try:
        ts_sent = parsedate_to_datetime(_header(msg, 'Date'))
        # data do PRIMEIRO Received:
        m = re.search(r';\s*(.+)', recvs[0]) if recvs else None
        if m:
            ts_recv = parsedate_to_datetime(m.group(1))
            _latency = ts_recv - ts_sent
    except Exception:
        pass

    return {
        "from_ip": from_ip,
        "to_ip": to_ip,
    }
