import asyncio


class EchoServerProtocol(asyncio.Protocol):
    def connection_made(self, transport):
        peername = transport.get_extra_info('peername')
        print('Connection from {}'.format(peername))
        self.transport = transport

    def data_received(self, data):
        message = data.decode()
        print('Data received: {!r}'.format(message))
        print('Send: {!r}'.format(message))
        self.transport.write(f'{message} - from server'.encode())
        print('Close the client socket')
        self.transport.close()


async def main():
    loop = asyncio.get_running_loop()
    server = await loop.create_server(
        lambda: EchoServerProtocol(),
        '127.0.0.1', 8866)

    async with server:
        await server.serve_forever()


asyncio.run(main())
