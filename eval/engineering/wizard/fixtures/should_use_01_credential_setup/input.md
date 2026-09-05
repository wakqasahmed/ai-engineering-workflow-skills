# Request

Set up our Twilio credentials for local dev and CI. We need `TWILIO_ACCOUNT_SID`
in `.env` and `TWILIO_AUTH_TOKEN` as both a local `.env` value and a GitHub
Actions secret, since `.github/workflows/sms-tests.yml` already references
`secrets.TWILIO_AUTH_TOKEN`.
