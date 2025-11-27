# dnie_im/crypto/protocol.py

"""
Simple protocol framing for the Noise IK messages and encrypted chat data.
Added FRAME_GOODBYE for explicit disconnect notification.
"""

import struct


class ProtocolFrame:
    """
    Basic frame format:
      4 bytes: total_length (excluding these 4 bytes)
      8 bytes: connection_id
      2 bytes: stream_id
      1 byte:  frame_type
      remaining: payload

    Frame types:
      0 = HANDSHAKE (initial Noise IK message)
      1 = DATA      (encrypted chat message)
      2 = ACK       (optional acknowledgment)
      3 = GOODBYE   (explicit disconnect notification)
    """

    FRAME_HANDSHAKE = 0
    FRAME_DATA = 1
    FRAME_ACK = 2
    FRAME_GOODBYE = 3  # NEW: Active disconnect notification

    @staticmethod
    def pack_frame(cid: bytes, stream_id: int, frame_type: int, payload: bytes) -> bytes:
        """
        Pack a protocol frame.
        """
        if len(cid) != 8:
            raise ValueError("connection_id must be 8 bytes")

        # total_length = 8 (cid) + 2 (stream_id) + 1 (type) + len(payload)
        total_length = 8 + 2 + 1 + len(payload)
        header = struct.pack("!I", total_length)  # 4 bytes
        header += cid  # 8 bytes
        header += struct.pack("!H", stream_id)  # 2 bytes
        header += struct.pack("!B", frame_type)  # 1 byte
        return header + payload

    @staticmethod
    def unpack_frame(data: bytes) -> tuple:
        """
        Unpack a protocol frame.
        Returns: (cid, stream_id, frame_type, payload)
        """
        if len(data) < 4:
            raise ValueError("Frame too short (no length field)")

        total_length = struct.unpack("!I", data[0:4])[0]
        if len(data) < 4 + total_length:
            raise ValueError("Incomplete frame")

        cid = data[4:12]
        stream_id = struct.unpack("!H", data[12:14])[0]
        frame_type = struct.unpack("!B", data[14:15])[0]
        payload = data[15 : 4 + total_length]

        return (cid, stream_id, frame_type, payload)
