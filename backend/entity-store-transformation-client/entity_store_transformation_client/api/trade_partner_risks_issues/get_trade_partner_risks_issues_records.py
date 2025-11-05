from http import HTTPStatus
from typing import Any, cast

import httpx

from ... import errors
from ...client import AuthenticatedClient, Client
from ...models.trade_partner_risks_issues_query_response import TradePartnerRisksIssuesQueryResponse
from ...types import UNSET, Response, Unset


def _get_kwargs(
    *,
    start: int | Unset = 0,
    limit: int | Unset = 20,
    expansion_level: int | Unset = 2,
) -> dict[str, Any]:
    params: dict[str, Any] = {}

    params["start"] = start

    params["limit"] = limit

    params["expansionLevel"] = expansion_level

    params = {k: v for k, v in params.items() if v is not UNSET and v is not None}

    _kwargs: dict[str, Any] = {
        "method": "get",
        "url": "/EntityService/TradePartnerRisksIssues/read",
        "params": params,
    }

    return _kwargs


def _parse_response(
    *, client: AuthenticatedClient | Client, response: httpx.Response
) -> Any | TradePartnerRisksIssuesQueryResponse | None:
    if response.status_code == 200:
        response_200 = TradePartnerRisksIssuesQueryResponse.from_dict(response.json())

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
) -> Response[Any | TradePartnerRisksIssuesQueryResponse]:
    return Response(
        status_code=HTTPStatus(response.status_code),
        content=response.content,
        headers=response.headers,
        parsed=_parse_response(client=client, response=response),
    )


def sync_detailed(
    *,
    client: AuthenticatedClient,
    start: int | Unset = 0,
    limit: int | Unset = 20,
    expansion_level: int | Unset = 2,
) -> Response[Any | TradePartnerRisksIssuesQueryResponse]:
    """Reads all TradePartnerRisksIssues records.

    Args:
        start (int | Unset):  Default: 0.
        limit (int | Unset):  Default: 20.
        expansion_level (int | Unset):  Default: 2.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Any | TradePartnerRisksIssuesQueryResponse]
    """

    kwargs = _get_kwargs(
        start=start,
        limit=limit,
        expansion_level=expansion_level,
    )

    response = client.get_httpx_client().request(
        **kwargs,
    )

    return _build_response(client=client, response=response)


def sync(
    *,
    client: AuthenticatedClient,
    start: int | Unset = 0,
    limit: int | Unset = 20,
    expansion_level: int | Unset = 2,
) -> Any | TradePartnerRisksIssuesQueryResponse | None:
    """Reads all TradePartnerRisksIssues records.

    Args:
        start (int | Unset):  Default: 0.
        limit (int | Unset):  Default: 20.
        expansion_level (int | Unset):  Default: 2.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Any | TradePartnerRisksIssuesQueryResponse
    """

    return sync_detailed(
        client=client,
        start=start,
        limit=limit,
        expansion_level=expansion_level,
    ).parsed


async def asyncio_detailed(
    *,
    client: AuthenticatedClient,
    start: int | Unset = 0,
    limit: int | Unset = 20,
    expansion_level: int | Unset = 2,
) -> Response[Any | TradePartnerRisksIssuesQueryResponse]:
    """Reads all TradePartnerRisksIssues records.

    Args:
        start (int | Unset):  Default: 0.
        limit (int | Unset):  Default: 20.
        expansion_level (int | Unset):  Default: 2.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Any | TradePartnerRisksIssuesQueryResponse]
    """

    kwargs = _get_kwargs(
        start=start,
        limit=limit,
        expansion_level=expansion_level,
    )

    response = await client.get_async_httpx_client().request(**kwargs)

    return _build_response(client=client, response=response)


async def asyncio(
    *,
    client: AuthenticatedClient,
    start: int | Unset = 0,
    limit: int | Unset = 20,
    expansion_level: int | Unset = 2,
) -> Any | TradePartnerRisksIssuesQueryResponse | None:
    """Reads all TradePartnerRisksIssues records.

    Args:
        start (int | Unset):  Default: 0.
        limit (int | Unset):  Default: 20.
        expansion_level (int | Unset):  Default: 2.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Any | TradePartnerRisksIssuesQueryResponse
    """

    return (
        await asyncio_detailed(
            client=client,
            start=start,
            limit=limit,
            expansion_level=expansion_level,
        )
    ).parsed
