from fastapi.requests import Request
import base64


async def extractors(iam, request: Request):
    user = None
    for extractor in iam.settings["extractors"]:
        user = await extractor(request).extract_token()
        if user:
            break
    return user


# This part is from guillotina https://github.com/plone/guillotina
class BasePolicy:
    name = "<FILL IN>"

    def __init__(self, request):
        self.request = request

    async def extract_token(self):
        """
        Extracts token from request.
        This will be a dictionary including something like {id, password},
        depending on the auth policy to authenticate user against
        """
        raise NotImplemented()


class BearerAuthPolicy(BasePolicy):
    name = "bearer"

    async def extract_token(self):
        header_auth = self.request.headers.get("AUTHORIZATION")
        if header_auth is not None:
            schema, _, encoded_token = header_auth.partition(" ")
            if schema.lower() == "bearer":
                return {"type": "bearer", "token": encoded_token.strip()}


class BasicAuthPolicy(BasePolicy):
    name = "basic"

    async def extract_token(self, value=None):
        if value is None:
            header_auth = self.request.headers.get("AUTHORIZATION")
        else:
            header_auth = value
        if header_auth is not None:
            schema, _, encoded_token = header_auth.partition(" ")
            if schema.lower() == "basic":
                try:
                    token = base64.b64decode(encoded_token).decode("utf-8")
                except Exception:  # pragma: no cover
                    # could be unicode, could be binascii generic,
                    # should just be ignored if we can't decode
                    return
                userid, _, password = token.partition(":")
                return {
                    "type": "basic",
                    "id": userid.strip(),
                    "token": password.strip(),
                }
