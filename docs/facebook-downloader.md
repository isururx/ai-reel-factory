# Facebook public video downloader (educational prototype)

This feature accepts a Facebook Reel/video URL and attempts to download a video that is publicly accessible without signing in.

## Boundaries
- Uses yt-dlp's Facebook extractor without cookies, browser profiles, credentials, or login sessions.
- Does not attempt private-video access, authentication bypass, or access-control circumvention.
- Only download content you own or have permission to download and process.
- Facebook may change its delivery mechanisms; public links are not guaranteed to be downloadable.
- Prototype limits: 300 MB and 15 minutes per video.

## Setup
From the backend directory, install dependencies:

```bash
pip install -e ".[dev]"
```

The backend API requires a valid Supabase access token.

## API
`POST /api/v1/downloads/facebook`

JSON body:

```json
{ "url": "https://www.facebook.com/reel/..." }
```

Returns an MP4 attachment when retrieval succeeds. Invalid, inaccessible, private, or unsupported videos return a clear 422 response.

## Notes
This is a synchronous prototype, not a production bulk downloader. Do not expose the endpoint publicly without rate limiting, request quotas, monitoring, and additional abuse protections.
