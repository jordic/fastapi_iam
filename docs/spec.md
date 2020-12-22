# Prupose

Build a user identification and registration service for
API based services.

## Identification

- Being able to identificate users using a Oauth2PassowrdFlow.
  User submits a username/password.
  The service provides a access token + refresh token

- Beign able to identificate users using an Oauth Provider (using authlib)

- Being able to identificate using private/public key for service accounts

- Beign able to authenticate with user/personal tokens (multiple passwords?)

## Registration

- Being able to registrate public users to the service.

  - Users can be registered with (user/password)
  - Users can be registered with a thirth party provider (authlib)
  - Provide a confirmation flow for the public registration.
    - Option A. An admin confirms the user
    - Option B. The user should confirm with a second factor (Email)

- Being able to create users on the system that can be identified, and
  determine the type of login required ()

- Being able to register users using a thirth party provider organization.
  Github Org / Google Suite / Microsoft ....

# Storage

- The package provides an storage layer around postgresql/asyncpg

## Docs research:

https://docs.microsoft.com/en-us/linkedin/shared/authentication/programmatic-refresh-tokens

When you use a refresh token to generate a new access token, the lifespan or Time To Live (TTL) of the refresh token remains the same as specified in the initial OAuth flow (365 days), and the new access token has a new TTL of 60 days.

https://developer.microsoft.com/en-us/identity/add-sign-in-with-microsoft

# Thouhgts on adding multitenacy

- Organization

  - groups
  - users

- User_Roles Organizations
