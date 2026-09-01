// download.ts — Turns a file response into a browser save dialog.
//
// The server already names the file in Content-Disposition, so that name
// is used when present rather than one invented on the client.

import type { HttpResponse } from "@angular/common/http";

export function saveResponseAsFile(
  response: HttpResponse<Blob>,
  fallbackName: string
): void {
  const disposition = response.headers.get("Content-Disposition") ?? "";
  const match = /filename\*?=(?:UTF-8'')?"?([^";]+)"?/i.exec(disposition);
  const filename = match ? decodeURIComponent(match[1]) : fallbackName;

  const url = window.URL.createObjectURL(response.body!);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  link.click();
  window.URL.revokeObjectURL(url);
}
