# Reference Video Ingestion

## Purpose

Reference videos belong to a specific Reference Page, which itself belongs to one AI Reel Factory Page workspace. The downloader is an ingestion option, not a separate competitor-scraping system.

## Ingestion paths

1. **Manual upload:** the user uploads a video file they are permitted to store and analyze.
2. **Public Facebook import:** the user supplies a public video/Reel URL. The existing yt-dlp downloader is used without cookies, login sessions, browser profiles, or access-control workarounds.
3. Both paths store the video in a private Cloudflare R2 bucket. PostgreSQL stores only the object key and metadata. Playback/download uses a short-lived presigned URL.

Prototype limits: 300 MB; MP4, WebM, MOV and MKV; Facebook import is limited by the downloader's 15-minute cap and public/no-login access requirement.

## Manual engagement and audience evidence

Views, reactions, shares and total comment count are optional manual fields. Blank values remain NULL and are never silently treated as zero. The user can also enter a sample of comments manually, one comment per line, plus notes describing where and when the metrics were observed.

These values are labelled as user-supplied evidence. They are not attributed to Meta or represented as verified API metrics. A manually entered total comment count can differ from the number of sample comments entered.

## Improved AI analysis pipeline

The ingestion work does not change the existing script-generation pipeline. It adds a future evidence-preparation stage for Reference Intelligence:

1. **Asset validation:** verify file size, MIME/signature, duration and ownership; retain immutable source metadata.
2. **Media extraction:** use FFmpeg to inspect duration, dimensions, frame rate and audio; generate low-resolution representative keyframes and an audio track.
3. **Transcript:** run speech-to-text where audio is present; retain timestamps and mark uncertain words rather than guessing.
4. **Creative analysis:** analyze hook, opening visual, scene sequence, pacing, narration, on-screen text, emotional tone, CTA and visual style. Store time-coded evidence for each finding.
5. **Audience/performance context:** separately summarize manually supplied metrics and manually entered comment samples. Do not infer reach, retention, watch time or demographics from unavailable data.
6. **Evidence-aware synthesis:** combine video observations and supplied context, with confidence and evidence references. Explicitly distinguish observed facts, user-entered data and model interpretations.
7. **Page-specific knowledge:** store approved insights under the owning Page workspace and Reference Page. Retrieve only insights belonging to that workspace when generating scripts.

## Safety and quality guardrails

- Analyze only videos the user is permitted to access, store and analyze. Do not bypass login, privacy settings, technical restrictions or platform controls.
- Do not republish or copy reference videos. Use analysis to learn high-level creative patterns and create original scripts and visuals.
- Never fabricate metrics, comments, transcripts, sources or timestamps.
- Treat comment samples as a sample, not a representative survey of all viewers.
- Require human review before an insight becomes reusable strategy knowledge.
- Keep the original video immutable. Re-uploads or edited assets create new video records/versions.
- Keep R2 objects private; return short-lived signed URLs only after ownership checks.

## Current implementation boundary

This branch implements private R2 ingestion, public Facebook URL import, manual engagement/comment entry, video listing and signed file access. The AI analysis job is intentionally left pending; analysis_status and analysis_result are prepared for the next analysis milestone. No claim is made that the uploaded video has already been analyzed.
