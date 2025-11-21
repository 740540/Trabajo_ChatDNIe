"""Protocol frame definitions and serialization"""

import struct
from typing import Tuple


class ProtocolFrame:
    """Frame structure: CID (8) || StreamID (2) || FrameType (1) || Length (2) || Payload"""
    
    # Frame types
    FRAME_HANDSHAKE = 0x01
    FRAME_DATA = 0x02
    FRAME_CONTROL = 0x03
    FRAME_AUTH_CHALLENGE = 0x04
    FRAME_AUTH_RESPONSE = 0x05
    
    @staticmethod
    def pack_frame(cid: bytes, stream_id: int, frame_type: int, payload: bytes) -> bytes:
        """Serialize frame for transmission"""
        header = struct.pack("!8sHBH", cid, stream_id, frame_type, len(payload))
        return header + payload
    
    @staticmethod
    def unpack_frame(data: bytes) -> Tuple[bytes, int, int, bytes]:
        """Deserialize received frame"""
        if len(data) < 13:
            raise Exception("Frame too short")
        
        header = struct.unpack("!8sHBH", data[:13])
        cid, stream_id, frame_type, length = header
        payload = data[13:13+length]
        return cid, stream_id, frame_type, payload
