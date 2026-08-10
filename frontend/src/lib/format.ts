const RELATIVE_UNITS: [Intl.RelativeTimeFormatUnit, number][] = [
  ["year", 60 * 60 * 24 * 365],
  ["month", 60 * 60 * 24 * 30],
  ["day", 60 * 60 * 24],
  ["hour", 60 * 60],
  ["minute", 60],
];

const relativeFormatter = new Intl.RelativeTimeFormat("en", { numeric: "auto" });
const dateFormatter = new Intl.DateTimeFormat("en", {
  month: "short",
  day: "numeric",
  year: "numeric",
  hour: "numeric",
  minute: "2-digit",
});

function toDate(iso: string): Date {
  // The backend returns naive timestamps (no timezone suffix) that are
  // actually UTC - force that interpretation instead of letting the
  // browser assume local time.
  const hasTimezone = /[zZ]|[+-]\d\d:?\d\d$/.test(iso);
  return new Date(hasTimezone ? iso : `${iso}Z`);
}

export function formatRelativeTime(iso: string): string {
  const date = toDate(iso);
  const seconds = (date.getTime() - Date.now()) / 1000;

  if (Math.abs(seconds) < 60) {
    return "just now";
  }

  for (const [unit, secondsInUnit] of RELATIVE_UNITS) {
    if (Math.abs(seconds) >= secondsInUnit) {
      return relativeFormatter.format(Math.round(seconds / secondsInUnit), unit);
    }
  }

  return dateFormatter.format(date);
}
