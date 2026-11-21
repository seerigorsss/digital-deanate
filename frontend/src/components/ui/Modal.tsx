import { useEffect, useId, useRef, type ReactNode } from 'react';
import { X } from 'lucide-react';
import { IconButton } from './Button';

interface ModalProps {
  open: boolean;
  onClose: () => void;
  title: string;
  children: ReactNode;
  footer?: ReactNode;
}

/**
 * Диалог на основе нативного <dialog>: фокус удерживается внутри, Esc закрывает.
 * На телефоне (< 640 px) выглядит как шторка снизу (bottom sheet).
 */
export function Modal({ open, onClose, title, children, footer }: ModalProps) {
  const ref = useRef<HTMLDialogElement>(null);
  const titleId = useId();

  useEffect(() => {
    const d = ref.current;
    if (!d) return;
    if (open && !d.open) d.showModal();
    if (!open && d.open) d.close();
  }, [open]);

  useEffect(() => {
    const d = ref.current;
    return () => {
      if (d?.open) d.close();
    };
  }, []);

  return (
    <dialog
      ref={ref}
      className="modal"
      aria-labelledby={titleId}
      onCancel={(e) => {
        e.preventDefault();
        onClose();
      }}
      onClick={(e) => {
        if (e.target === ref.current) onClose();
      }}
    >
      {open && (
        <>
          <div className="modal__head">
            <h2 className="modal__title" id={titleId}>
              {title}
            </h2>
            <IconButton label="Закрыть" onClick={onClose}>
              <X aria-hidden="true" />
            </IconButton>
          </div>
          <div className="modal__body">{children}</div>
          {footer && <div className="modal__foot">{footer}</div>}
        </>
      )}
    </dialog>
  );
}
