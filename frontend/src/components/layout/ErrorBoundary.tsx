import { Component, type ErrorInfo, type ReactNode } from 'react';
import { RefreshCw, TriangleAlert } from 'lucide-react';
import { EmptyState } from '../ui/States';
import { Button } from '../ui/Button';

interface State {
  failed: boolean;
}

/** Защита от непредвиденной ошибки отрисовки: показываем экран «Что-то пошло не так», а не белую страницу. */
export class ErrorBoundary extends Component<{ children: ReactNode }, State> {
  state: State = { failed: false };

  static getDerivedStateFromError(): State {
    return { failed: true };
  }

  componentDidCatch(_error: Error, _info: ErrorInfo): void {
    // Ошибка уже обработана отображением запасного экрана.
  }

  render() {
    if (this.state.failed) {
      return (
        <div className="card">
          <EmptyState
            tone="danger"
            icon={<TriangleAlert />}
            title="Что-то пошло не так"
            text="Попробуйте обновить страницу. Если ошибка повторится — зайдите позже."
            actions={
              <Button variant="secondary" icon={<RefreshCw aria-hidden="true" />} onClick={() => window.location.reload()}>
                Обновить страницу
              </Button>
            }
          />
        </div>
      );
    }
    return this.props.children;
  }
}
