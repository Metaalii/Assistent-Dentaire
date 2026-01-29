import React, { Component, ErrorInfo, ReactNode } from 'react';
import { AlertCircleIcon, RefreshIcon } from './ui/Icons';
import { Button } from './ui';

interface Props {
  children: ReactNode;
  fallback?: ReactNode;
  onError?: (error: Error, errorInfo: ErrorInfo) => void;
}

interface State {
  hasError: boolean;
  error: Error | null;
  errorInfo: ErrorInfo | null;
}

/**
 * Error Boundary component for catching and displaying React errors gracefully.
 * Prevents the entire app from crashing when a component throws an error.
 */
class ErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = {
      hasError: false,
      error: null,
      errorInfo: null,
    };
  }

  static getDerivedStateFromError(error: Error): Partial<State> {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo): void {
    this.setState({ errorInfo });

    // Log error to console in development
    console.error('ErrorBoundary caught an error:', error, errorInfo);

    // Call custom error handler if provided
    this.props.onError?.(error, errorInfo);
  }

  handleRetry = (): void => {
    this.setState({
      hasError: false,
      error: null,
      errorInfo: null,
    });
  };

  handleReload = (): void => {
    window.location.reload();
  };

  render(): ReactNode {
    if (this.state.hasError) {
      // Custom fallback if provided
      if (this.props.fallback) {
        return this.props.fallback;
      }

      // Default error UI
      return (
        <div className="min-h-[400px] flex items-center justify-center p-8">
          <div className="max-w-md w-full bg-white rounded-2xl shadow-xl border border-red-100 p-8 text-center">
            {/* Error icon */}
            <div className="mx-auto w-16 h-16 rounded-2xl bg-gradient-to-br from-red-500 to-red-600 shadow-lg shadow-red-500/30 flex items-center justify-center mb-6">
              <AlertCircleIcon className="text-white" size={32} />
            </div>

            {/* Error title */}
            <h2 className="text-xl font-bold text-[#1e293b] mb-3">
              Une erreur est survenue
            </h2>

            {/* Error description */}
            <p className="text-[#64748b] mb-6">
              Quelque chose s'est mal passe. Veuillez reessayer ou recharger la page.
            </p>

            {/* Error details (collapsed by default) */}
            {this.state.error && (
              <details className="mb-6 text-left">
                <summary className="cursor-pointer text-sm text-[#94a3b8] hover:text-[#64748b]">
                  Details techniques
                </summary>
                <div className="mt-2 p-3 bg-red-50 rounded-lg border border-red-100 overflow-auto max-h-32">
                  <code className="text-xs text-red-700 whitespace-pre-wrap break-all">
                    {this.state.error.message}
                  </code>
                </div>
              </details>
            )}

            {/* Action buttons */}
            <div className="flex gap-3 justify-center">
              <Button
                variant="primary"
                onClick={this.handleRetry}
                leftIcon={<RefreshIcon size={16} />}
              >
                Reessayer
              </Button>
              <Button
                variant="secondary"
                onClick={this.handleReload}
              >
                Recharger la page
              </Button>
            </div>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}

/**
 * HOC to wrap a component with ErrorBoundary
 */
export function withErrorBoundary<P extends object>(
  WrappedComponent: React.ComponentType<P>,
  fallback?: ReactNode
): React.FC<P> {
  const displayName = WrappedComponent.displayName || WrappedComponent.name || 'Component';

  const ComponentWithBoundary: React.FC<P> = (props) => (
    <ErrorBoundary fallback={fallback}>
      <WrappedComponent {...props} />
    </ErrorBoundary>
  );

  ComponentWithBoundary.displayName = `withErrorBoundary(${displayName})`;
  return ComponentWithBoundary;
}

export default ErrorBoundary;
