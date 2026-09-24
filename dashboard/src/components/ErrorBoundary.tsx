import { Component, type ErrorInfo, type ReactNode } from "react";

interface Props {
  name: string;            // the view, for the message ("Signals", "the map", …)
  resetKey?: string;       // when it changes (another recording or tab), the view is tried again
  children: ReactNode;
}
interface State { error: Error | null; key?: string }

/** Release 1.0 — contain a failing view: one view that throws shows a short message and a retry button; the rest
 *  of the dashboard (map, tabs, time controls, presenter keys) keeps working. Nothing is hidden: the error text is
 *  shown and logged. */
export class ErrorBoundary extends Component<Props, State> {
  state: State = { error: null, key: this.props.resetKey };

  static getDerivedStateFromError(error: Error): Partial<State> {
    return { error };
  }

  static getDerivedStateFromProps(props: Props, state: State): Partial<State> | null {
    return props.resetKey !== state.key ? { error: null, key: props.resetKey } : null;
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    console.error(`PRAHARI-SIM: the ${this.props.name} view failed`, error, info.componentStack);
  }

  render() {
    if (!this.state.error) return this.props.children;
    return (
      <div className="view-error" role="alert" data-testid="view-error">
        <b>The {this.props.name} view could not be drawn.</b> The other views still work.
        <div className="small muted mono">{this.state.error.message}</div>
        <button onClick={() => this.setState({ error: null })}>Try again</button>
      </div>
    );
  }
}
