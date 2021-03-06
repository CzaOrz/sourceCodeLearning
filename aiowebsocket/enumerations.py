from enum import IntEnum

__all__ = ['SocketState', 'DataFrames', 'ControlFrames', 'StatusCodes']

StatusCodes = [1000, 1001, 1002, 1003, 1007, 1008, 1009, 1010, 1011]


class SocketState(IntEnum):
    zero, connecting, opened, closing, closed = (0, 0, 1, 2, 3)


class DataFrames(IntEnum):
    cont, text, binary = (0x00, 0x01, 0x02)


class ControlFrames(IntEnum):
    close, ping, pong = (0x08, 0x09, 0x0A)
