# Advent of Code Discord Leaderboard

## Overview
Posts the Advent of Code Leaderboard to a channel daily via a Discord webhook.

Hosted via **AWS Lambda**.

## Setup
### Setting up `.env`
`TEST_MODE` can be set to `True` or `False`. If `True`, leaderboard data is received via a local `JSON` file; otherwise, a request is made to the Advent of Code API.

`SESSION_COOKIE` is the cookie from accessing the Advent of Code website.
> Note: `SESSION_COOKIE` typically expires after a month, but that should be long enough for Advent of Code (December)

`PRIVATE_LEADERBOARD_CODE` is the prefix of the leaderboard join code. For example, if your join code is `#####-ABCDEF`, the `PRIVATE_LEADERBOARD_CODE` is `#####`.

`WEBHOOK_URL` is the Discord webhook url for the channel.