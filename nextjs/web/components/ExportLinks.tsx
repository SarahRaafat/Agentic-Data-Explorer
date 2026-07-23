"use client";

import { exportDownloadUrl } from "@/lib/api";
import type { ExportItem } from "@/lib/types";

export default function ExportLinks({ exports }: { exports: ExportItem[] }) {
  if (!exports.length) return null;
  return (
    <div>
      <h4 className="section-title">Exports</h4>
      <div className="export-row">
        {exports.map((item, i) => {
          const path = item.path || "";
          const name = path.split(/[/\\]/).pop() || item.format || `export-${i}`;
          const href = path ? exportDownloadUrl(path) : undefined;
          return href ? (
            <a
              key={`${name}-${i}`}
              className="btn btn-sm"
              href={href}
              download={name}
              target="_blank"
              rel="noreferrer"
            >
              Download {item.format || name}
            </a>
          ) : (
            <span key={i} className="caption">
              {item.note || name}
            </span>
          );
        })}
      </div>
    </div>
  );
}
