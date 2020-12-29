""" Testing helpers """
from functools import partial


async def login(client, username, password) -> "Client":
    res = await client.post(
        "/auth/login",
        form={"username": username, "password": password},
    )
    assert res.status_code == 200
    return Client(client, res.json()["access_token"])


def auth_header(token):
    return {"Authorization": f"Bearer {token}"}


class Client:
    def __init__(self, client, access_token):
        self.client = client
        self.token = access_token

    def __getattr__(self, name):
        func = getattr(self.client, name)
        return partial(func, headers=auth_header(self.token))
