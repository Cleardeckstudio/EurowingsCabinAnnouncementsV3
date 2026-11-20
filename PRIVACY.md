# Privacy & Data Protection (GDPR / CNIL)

Cleardeck Studio takes privacy seriously. This document explains how this add-on handles data, in line with the EU General Data Protection Regulation (GDPR) and French CNIL guidance.

## What this add-on does

This is a local desktop tool for Microsoft Flight Simulator 2024. It generates voice announcement audio files for the Fenix A320 using Microsoft's text-to-speech (Azure/Edge TTS) service.

## What data is processed

- **No personal data is collected, stored, or transmitted by Cleardeck Studio.** The add-on runs entirely on your own computer.
- To generate announcements, the add-on reads your own SimBrief flight plan (flight number, route, times) that you provide yourself, and sends the announcement text to Microsoft's public text-to-speech service to produce the audio. This text contains flight details (airline, flight number, airports, weather) — not personal information about you.
- Any name you enter during setup (e.g. a captain/crew name) is stored only in a local configuration file on your own computer and is never transmitted anywhere except as spoken text in the generated audio.
- No analytics, telemetry, or tracking of any kind is built into this add-on.

## Your rights

Since no personal data is collected or stored by us, there is no data of yours for us to access, correct, or delete. If you believe this is inaccurate or have any concern, please open an Issue on this repository.

## Contact

Questions about this add-on's data handling can be raised via a GitHub Issue on this repository.
