#!/usr/bin/env python3
"""Plot day gaps between adjacent dates as an SVG."""

import argparse
from datetime import datetime
from math import ceil, floor
from pathlib import Path


def read_gaps(path):
    gaps = []
    previous = None

    for number, line in enumerate(path.read_text().splitlines(), 1):
        value = line.strip()
        if not value:
            continue
        if value == "...":
            previous = None
            continue

        try:
            current = datetime.strptime(value, "%m/%d/%Y").date()
            if current.strftime("%m/%d/%Y") != value:
                raise ValueError
        except ValueError:
            raise ValueError(
                f"{path}:{number}: invalid date {value!r}; expected MM/DD/YYYY"
            ) from None

        if previous is not None:
            gaps.append((current - previous).days)
        previous = current

    return gaps


def regression(values):
    n = len(values)
    if n < 2:
        raise ValueError("at least two date intervals are required")

    sx = n * (n + 1) / 2
    sy = sum(values)
    sxx = n * (n + 1) * (2 * n + 1) / 6
    sxy = sum(x * y for x, y in enumerate(values, 1))
    slope = (n * sxy - sx * sy) / (n * sxx - sx * sx)
    return slope, (sy - slope * sx) / n


def make_svg(values, slope, intercept):
    width, height = 960, 600
    left, right, top, bottom = 85, 35, 55, 75
    plot_width = width - left - right
    plot_height = height - top - bottom
    n = len(values)

    fitted = [slope + intercept, slope * n + intercept]
    low = min(*values, *fitted)
    high = max(*values, *fitted)
    padding = (high - low) * 0.1 or 1
    low = floor(low - padding)
    high = ceil(high + padding)
    tick_step = max(1, ceil((high - low) / 5))
    high = low + tick_step * ceil((high - low) / tick_step)
    average = sum(values) / n

    def px(x):
        return left + (x - 1) * plot_width / (n - 1)

    def py(y):
        return top + (high - y) * plot_height / (high - low)

    out = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        '<rect width="100%" height="100%" fill="white"/>',
        '<g font-family="sans-serif" fill="#222">',
        f'<text x="{width / 2}" y="30" text-anchor="middle" font-size="20">Days Between Adjacent Dates</text>',
    ]

    for tick in range(low, high + 1, tick_step):
        y = py(tick)
        out += [
            f'<line x1="{left}" y1="{y:.2f}" x2="{width - right}" y2="{y:.2f}" stroke="#ddd"/>',
            f'<text x="{left - 10}" y="{y + 4:.2f}" text-anchor="end" font-size="12">{tick}</text>',
        ]

    ticks = range(1, n + 1) if n <= 12 else sorted(
        {round(1 + i * (n - 1) / 9) for i in range(10)}
    )
    for tick in ticks:
        x = px(tick)
        out += [
            f'<line x1="{x:.2f}" y1="{top}" x2="{x:.2f}" y2="{height - bottom}" stroke="#eee"/>',
            f'<text x="{x:.2f}" y="{height - bottom + 22}" text-anchor="middle" font-size="12">{tick}</text>',
        ]

    out += [
        f'<line x1="{left}" y1="{top}" x2="{left}" y2="{height - bottom}" stroke="#222"/>',
        f'<line x1="{left}" y1="{height - bottom}" x2="{width - right}" y2="{height - bottom}" stroke="#222"/>',
        f'<text x="{left + plot_width / 2}" y="{height - 22}" text-anchor="middle" font-size="14">Interval number</text>',
        f'<text x="22" y="{top + plot_height / 2}" text-anchor="middle" font-size="14" transform="rotate(-90 22 {top + plot_height / 2})">Days since preceding date</text>',
    ]

    points = " ".join(f"{px(x):.2f},{py(y):.2f}" for x, y in enumerate(values, 1))
    out.append(f'<polyline points="{points}" fill="none" stroke="#1769aa" stroke-width="2"/>')
    for x, value in enumerate(values, 1):
        out.append(
            f'<circle cx="{px(x):.2f}" cy="{py(value):.2f}" r="4" fill="#1769aa"><title>Interval {x}: {value} days</title></circle>'
        )

    out += [
        f'<line x1="{px(1):.2f}" y1="{py(average):.2f}" x2="{px(n):.2f}" y2="{py(average):.2f}" stroke="#6a1b9a" stroke-width="2" stroke-dasharray="2 4"/>',
        f'<line x1="{px(1):.2f}" y1="{py(fitted[0]):.2f}" x2="{px(n):.2f}" y2="{py(fitted[1]):.2f}" stroke="#c62828" stroke-width="2.5" stroke-dasharray="8 5"/>',
        f'<line x1="{width - 255}" y1="{top + 18}" x2="{width - 215}" y2="{top + 18}" stroke="#1769aa" stroke-width="2"/>',
        f'<text x="{width - 205}" y="{top + 22}" font-size="12">Day gaps</text>',
        f'<line x1="{width - 255}" y1="{top + 38}" x2="{width - 215}" y2="{top + 38}" stroke="#c62828" stroke-width="2.5" stroke-dasharray="8 5"/>',
        f'<text x="{width - 205}" y="{top + 42}" font-size="12">Regression (slope {slope:.2f})</text>',
        f'<line x1="{width - 255}" y1="{top + 58}" x2="{width - 215}" y2="{top + 58}" stroke="#6a1b9a" stroke-width="2" stroke-dasharray="2 4"/>',
        f'<text x="{width - 205}" y="{top + 62}" font-size="12">Average ({average:.1f} days)</text>',
        '</g></svg>',
    ]
    return "\n".join(out) + "\n"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", nargs="?", type=Path, default=Path("README.org"))
    parser.add_argument("-o", "--output", type=Path, default=Path("plot.svg"))
    args = parser.parse_args()

    try:
        values = read_gaps(args.input)
        slope, intercept = regression(values)
        args.output.write_text(make_svg(values, slope, intercept))
    except (OSError, ValueError) as error:
        parser.error(str(error))

    print(f"Wrote {args.output}")


if __name__ == "__main__":
    main()
