# Third-Party Notices

SlideBridge Core includes selected third-party assets that are redistributed
under their own open-source licenses.

## OpenSeadragon

- Project: OpenSeadragon
- Version: 4.1.0
- Source package: `openseadragon` npm package
- License: BSD-3-Clause
- Bundled files:
  - `slidebridge/server/static/vendor/openseadragon/openseadragon.min.js`
  - `slidebridge/server/static/vendor/openseadragon/images/*.png`
  - `slidebridge/server/static/vendor/openseadragon/LICENSE.txt`

The bundled viewer asset lets the local SlideBridge viewer work without waiting
for a CDN request. A CDN fallback remains available if the local asset is
missing or unavailable.
