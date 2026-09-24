import { LineChart, ScatterChart } from "echarts/charts";
import { GridComponent, LegendComponent, MarkAreaComponent, MarkLineComponent, TitleComponent,
         TooltipComponent } from "echarts/components";
import * as echarts from "echarts/core";
import { CanvasRenderer } from "echarts/renderers";
import { useEffect, useRef } from "react";

echarts.use([LineChart, ScatterChart, GridComponent, LegendComponent, TooltipComponent, MarkLineComponent,
             MarkAreaComponent, TitleComponent, CanvasRenderer]);

export type EOption = echarts.EChartsCoreOption;

/** Thin ECharts wrapper: one chart per div, options merged on change, resized with its container. */
export function EChart({ option, height, onClick, testId }: {
  option: EOption; height: number; onClick?: () => void; testId?: string;
}) {
  const ref = useRef<HTMLDivElement>(null);
  const chart = useRef<echarts.ECharts | null>(null);

  useEffect(() => {
    if (!ref.current) return;
    const c = echarts.init(ref.current, undefined, { renderer: "canvas" });
    chart.current = c;
    const ro = new ResizeObserver(() => c.resize());
    ro.observe(ref.current);
    return () => { ro.disconnect(); c.dispose(); chart.current = null; };
  }, []);

  useEffect(() => { chart.current?.setOption(option); }, [option]);

  return <div ref={ref} style={{ height, cursor: onClick ? "pointer" : undefined }} onClick={onClick}
              className="echart" data-testid={testId} />;
}
