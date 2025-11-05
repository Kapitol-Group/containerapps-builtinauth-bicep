from http import HTTPStatus
from typing import Any, cast
from uuid import UUID

import httpx

from ... import errors
from ...client import AuthenticatedClient, Client
from ...models.trade_partner_recognition import TradePartnerRecognition
from ...types import UNSET, Response, Unset


def _get_kwargs(
    id: UUID,
    *,
    expansion_level: int | Unset = 2,
) -> dict[str, Any]:
    params: dict[str, Any] = {}

    params["expansionLevel"] = expansion_level

    params = {k: v for k, v in params.items() if v is not UNSET and v is not None}

    _kwargs: dict[str, Any] = {
        "method": "get",
        "url": f"/EntityService/TradePartnerRecognition/read/{id}",
        "params": params,
    }

    return _kwargs


def _parse_response(
    *, client: AuthenticatedClient | Client, response: httpx.Response
) -> Any | TradePartnerRecognition | None:
    if response.status_code == 200:
        response_200 = TradePartnerRecognition.from_dict(response.json())

        return response_200

    if response.status_code == 401:
        response_401 = cast(Any, None)
        return response_401

    if response.status_code == 403:
        response_403 = cast(Any, None)
        return response_403

    if client.raise_on_unexpected_status:
        raise errors.UnexpectedStatus(response.status_code, response.content)
    else:
        return None


def _build_response(
    *, client: AuthenticatedClient | Client, response: httpx.Response
) -> Response[Any | TradePartnerRecognition]:
    return Response(
        status_code=HTTPStatus(response.status_code),
        content=response.content,
        headers=response.headers,
        parsed=_parse_response(client=client, response=response),
    )


def sync_detailed(
    id: UUID,
    *,
    client: AuthenticatedClient,
    expansion_level: int | Unset = 2,
) -> Response[Any | TradePartnerRecognition]:
    """Retrieves a single TradePartnerRecognition record by Id.

    Args:
        id (UUID):
        expansion_level (int | Unset):  Default: 2.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Any | TradePartnerRecognition]
    """

    kwargs = _get_kwargs(
        id=id,
        expansion_level=expansion_level,
    )

    response = client.get_httpx_client().request(
        **kwargs,
    )

    return _build_response(client=client, response=response)


def sync(
    id: UUID,
    *,
    client: AuthenticatedClient,
    expansion_level: int | Unset = 2,
) -> Any | TradePartnerRecognition | None:
    """Retrieves a single TradePartnerRecognition record by Id.

    Args:
        id (UUID):
        expansion_level (int | Unset):  Default: 2.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Any | TradePartnerRecognition
    """

    return sync_detailed(
        id=id,
        client=client,
        expansion_level=expansion_level,
    ).parsed


async def asyncio_detailed(
    id: UUID,
    *,
    client: AuthenticatedClient,
    expansion_level: int | Unset = 2,
) -> Response[Any | TradePartnerRecognition]:
    """Retrieves a single TradePartnerRecognition record by Id.

    Args:
        id (UUID):
        expansion_level (int | Unset):  Default: 2.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Any | TradePartnerRecognition]
    """

    kwargs = _get_kwargs(
        id=id,
        expansion_level=expansion_level,
    )

    response = await client.get_async_httpx_client().request(**kwargs)

    return _build_response(client=client, response=response)


async def asyncio(
    id: UUID,
    *,
    client: AuthenticatedClient,
    expansion_level: int | Unset = 2,
) -> Any | TradePartnerRecognition | None:
    """Retrieves a single TradePartnerRecognition record by Id.

    Args:
        id (UUID):
        expansion_level (int | Unset):  Default: 2.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Any | TradePartnerRecognition
    """

    return (
        await asyncio_detailed(
            id=id,
            client=client,
            expansion_level=expansion_level,
        )
    ).parsed
