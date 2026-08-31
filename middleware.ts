const PIN_TOKEN = "a3f9c2e17b6d4508";

export const config = {
  matcher: ["/wiki/:path*"],
};

export default function middleware(request: Request) {
  const url = new URL(request.url);

  if (url.pathname === "/wiki/pin.html") {
    return undefined;
  }

  const cookieHeader = request.headers.get("cookie") || "";
  const authed = cookieHeader
    .split(";")
    .map((c) => c.trim())
    .some((c) => c === `wiki_auth=${PIN_TOKEN}`);

  if (authed) {
    return undefined;
  }

  const back = encodeURIComponent(url.pathname + url.search);
  const redirectUrl = new URL(`/wiki/pin.html?back=${back}`, url.origin);
  return Response.redirect(redirectUrl, 302);
}
