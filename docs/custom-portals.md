# Custom portals

Select **Custom website** in the desktop and choose a directory containing `index.html`. Relative assets, local JavaScript, CSS, images, and nested directory indexes are supported. Hidden files, directory listings, and paths outside the selected directory are not served. Each file is limited to 32 MiB.

Use local assets for offline hosting. Absolute public CDN URLs cannot load without internet access. Captive mini-browsers may restrict downloads, popups, external applications, and some JavaScript APIs.

## Confirm access

The included `examples/custom-portal` directory demonstrates the flow:

1. Fetch `GET /captivate/token` from the portal origin.
2. Read the JSON `token` value.
3. Submit an HTML form using `POST /captivate/continue`, with `Content-Type: application/x-www-form-urlencoded` and a `token` field.
4. Captivate redirects a successful confirmation to `/captivate/success`.

The token is bound to the requesting peer. Confirmation requests are limited to ten attempts per minute per IP. Access uses the session's configured duration and optional uplink.

For the built-in terms template, submit `accept=yes`. For the built-in voucher template, submit `voucher=<configured-code>`. Validation always takes place on the server.

**Custom website mode allows confirmation with a valid token.** A check implemented only in browser JavaScript can be bypassed. Use the built-in voucher mode for enforced pre-issued codes. Custom payment, identity, or business-rule verification needs a trusted server-side integration; it cannot be enforced by changing the static page alone.

## Inspect state

`GET /captivate/api` returns `application/captive+json` with `captive` and `user-portal-url` fields. Offline sessions remain captive because confirmation cannot supply internet connectivity. This local HTTP endpoint is not advertised as an RFC 8908 HTTPS service.

## Preview

```bash
.venv/bin/python scripts/preview.py --template custom --directory examples/custom-portal
```

Open the printed loopback URL. Preview confirmations simulate success without changing networking. Stop the process with Ctrl+C.
