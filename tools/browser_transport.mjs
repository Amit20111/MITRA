export function validateUrl(value, origins) {
  const url = new URL(value);
  if (
    !Array.isArray(origins) ||
    url.href.length > 2000 ||
    !origins.includes(url.origin) ||
    !["http:", "https:"].includes(url.protocol) ||
    url.username ||
    url.password ||
    url.hash
  ) {
    throw new Error("Origin or URL denied");
  }
  return url.href;
}

export async function fetchDocument(requested, origins, signal) {
  let url = validateUrl(requested, origins);
  let response;
  for (let redirects = 0; redirects <= 3; redirects++) {
    response = await fetch(url, {
      method: "GET",
      redirect: "manual",
      signal,
      headers: {
        Accept: "text/html,text/plain",
        "User-Agent": "MITRA-ReadOnly/1",
      },
    });
    if (response.status >= 300 && response.status < 400) {
      await response.body?.cancel();
      if (redirects === 3 || !response.headers.get("location"))
        throw new Error("Redirect limit");
      url = validateUrl(new URL(response.headers.get("location"), url).href);
    } else break;
  }
  if (!response?.ok) throw new Error("Unsuccessful page status");
  const mime = response.headers.get("content-type")?.split(";")[0].trim();
  if (
    !["text/html", "text/plain"].includes(mime) ||
    response.headers.has("content-disposition")
  ) {
    throw new Error("Unsupported document or download");
  }
  const chunks = [];
  let bytes = 0;
  for await (const chunk of response.body) {
    bytes += chunk.length;
    if (bytes > 1024 * 1024) {
      await response.body.cancel().catch(() => {});
      throw new Error("Page exceeds 1 MB");
    }
    chunks.push(chunk);
  }
  return { url, body: Buffer.concat(chunks), mime };
}

export const documentHeaders = (mime) => ({
  "content-type": `${mime}; charset=utf-8`,
  "content-security-policy":
    "default-src 'none'; style-src 'unsafe-inline'; form-action 'none'; frame-src 'none'; sandbox",
});
