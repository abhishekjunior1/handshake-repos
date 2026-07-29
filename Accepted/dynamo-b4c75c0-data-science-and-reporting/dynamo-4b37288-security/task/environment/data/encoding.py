"""BinVault encoding utilities."""
import base64


def decode_data(data, encoding):
    """Decode stored bytes. 0=raw, 1=base64, 2=hex."""
    if encoding == 0:
        return data
    elif encoding == 1:
        return base64.b64decode(data)
    elif encoding == 2:
        return bytes.fromhex(data.decode('ascii'))
    raise ValueError(f"unknown encoding {encoding}")
