import { ReactNode } from "react";
import "./ColumnItem.css";

interface ColumnItemProps {
  readonly active: boolean;
  readonly startTime: number;
  readonly onClick: () => void;
  readonly children: ReactNode;
}

export const ColumnItem = ({ active, startTime, onClick, children }: ColumnItemProps) => (
  <div
    className={`column-item${active ? " column-item--active" : ""}`}
    data-start-time={startTime}
    onClick={onClick}
  >
    {children}
  </div>
);
