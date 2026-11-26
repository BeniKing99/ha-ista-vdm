# Ista VDM for Home Assistant

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://github.com/hacs/integration)
[![Release](https://img.shields.io/github/v/release/BeniKing99/ha-ista-vdm)](https://github.com/BeniKing99/ha-ista-vdm/releases/latest)

This is a custom integration for Home Assistant that retrieves heating, hot water and cold water consumption data from the ista VDM (Verbrauchsdatenmanagement) portal.

## Latest Release

**[v1.1.3](https://github.com/BeniKing99/ha-ista-vdm/releases/tag/v1.1.3)**: a temporary outage of the ista portal no longer asks for your password; Home Assistant retries the connection instead.
Since [v1.1.0](https://github.com/BeniKing99/ha-ista-vdm/releases/tag/v1.1.0): support for multiple flats per account and a new cold water sensor.
See all [releases](https://github.com/BeniKing99/ha-ista-vdm/releases) for the full changelog.

## Features

- [DATA] **Automatic Data Retrieval**: Fetches consumption data once per day
- [HOME] **Complete History**: Full historical data in sensor attributes  
- [BUILDING] **Flat Information**: Displays address, square meters, and other details
- [HOME] **Multiple Flats**: Every flat of your account gets its own device
- [WATER] **Cold Water**: Separate sensor for flats with a cold water meter
- [WORLD] **Multi-Language**: English, German, French, Spanish support
- [SYNC] **Re-authentication**: Easy password updates via UI
- [CHART] **Diagnostics**: Download diagnostic data for troubleshooting

## Installation

**Home Assistant 2026.11 or newer** (HACS is built in as the Marketplace):

1. Go to **Settings** -> **Marketplace**
2. Select **Add from link** and enter `https://github.com/BeniKing99/ha-ista-vdm`
3. Open "Ista VDM" and select **Install**. The setup flow opens right away, no restart needed

**Home Assistant 2026.10 or older** (HACS):

1. Ensure [HACS](https://hacs.xyz/) is installed
2. In HACS, open the menu (...) -> **Custom repositories**
3. Add `https://github.com/BeniKing99/ha-ista-vdm` with the type **Integration**
4. Search for "Ista VDM" and select **Download**
5. Restart Home Assistant

## Configuration

After installing from the Marketplace, the setup flow opens automatically (start at step 4). Otherwise:

1. Go to **Settings** -> **Devices & Services**
2. Click **Add Integration**
3. Search for "Ista VDM"
4. Enter your ista VDM portal credentials
5. Click **Submit**

## Support

- [GitHub Issues](https://github.com/BeniKing99/ha-ista-vdm/issues)
- [Documentation](https://github.com/BeniKing99/ha-ista-vdm/blob/main/README.md)

## License

MIT License
