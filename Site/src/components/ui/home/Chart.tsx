"use client";

import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  CartesianGrid,
} from 'recharts';
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome';
import { faCircle, faMoneyBill } from '@fortawesome/free-solid-svg-icons';

type DataPoint = {
  date: string;
  value: number;
};

type ChartProps = {
  data: DataPoint[];
  color?: string;
  className?: string;
};

export function CustomLineChart({
  data,
  color = '#6366f1',
  className,
}: ChartProps) {
  return (
    <div
      className={`relative w-full h-60 md:h-80 bg-background shadow-sm border border-foreground/10 border-dashed focus:outline-none select-none [&_.recharts-sector]:outline-none [&_.recharts-surface]:outline-none [&_.recharts-layer]:outline-none ${className}`}
      style={{ minHeight: '240px' }}
    >
      <ResponsiveContainer width="100%" height="100%" minHeight={240} style={{ outline: 'none' }}>
        <LineChart
          data={data}
          margin={{ top: 30, right: 30, left: 0, bottom: 20 }}
          style={{ outline: 'none' }}
        >
          <CartesianGrid strokeDasharray="4 4" stroke="#454545" strokeWidth={1} />
          <XAxis
            dataKey="date"
            stroke="transparent"
            tick={{ fill: '#ffffff', fontSize: 12, fontWeight: 500 }}
            tickMargin={12}
          />
          <YAxis
            stroke="transparent"
            tick={{ fill: '#ffffff', fontSize: 12 }}
          />
          <Tooltip
            content={<CustomTooltip />}
            wrapperStyle={{ outline: 'none' }}
          />
          <Line
            type="monotone"
            dataKey="value"
            stroke={color}
            strokeWidth={3}
            dot={{ r: 5, stroke: '#fff', strokeWidth: 2 }}
            activeDot={{ r: 8 }}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}

function CustomTooltip({
  active,
  payload,
  label,
}: {
  active?: boolean;
  payload?: any[];
  label?: string;
}) {
  if (!active || !payload || !payload.length) return null;

  return (
    <div className="rounded-md border border-foreground/10 bg-background px-3 py-2 shadow-xl text-sm space-y-2 min-w-[10rem]">
      <div className="font-medium text-foreground text-sm flex items-center justify-between gap-5">
        <span className="text-muted-foreground/80 text-[12px]">Venda realizada</span>
        <span className="font-semibold text-foreground text-[12px]">{label}</span>
      </div>
      <hr className="border-foreground/10 my-2" />
      <div className="flex items-center justify-between items-center">
        <span className="text-muted-foreground/80 text-[12px]">Valor</span>
        <span className="font-semibold text-foreground text-[12px]">
          R$ {payload[0].value.toLocaleString()}
        </span>
      </div>
    </div>
  );
}
