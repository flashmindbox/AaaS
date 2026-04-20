# apps/

End-user applications. Each app is a deployable unit.

| Planned app    | Phase | Stack                                          |
| -------------- | ----- | ---------------------------------------------- |
| `widget/`      | 1     | Preact + Shadow DOM — drop-in accessibility UI |
| `dashboard/`   | 1     | Next.js + React + Radix — tenant admin UI      |
| `saralaccess/` | 4     | React Native — citizen mobile app              |
| `kiosk/`       | 4     | Android kiosk app                              |
| `exam/`        | 3     | Next.js — accessible exam delivery             |

Apps consume `@aaas/ui`, `@aaas/config`, and services via the API gateway.
