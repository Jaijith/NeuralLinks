import React from 'react';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { AlertTriangle } from 'lucide-react';

/**
 * @typedef {Object} ConfirmDialogProps
 * @property {boolean} open - Whether the dialog is open
 * @property {function} onOpenChange - Handler for open state changes
 * @property {string} title - Dialog title
 * @property {string} [description] - Dialog description
 * @property {string} [confirmLabel] - Confirm button label (default: "Confirm")
 * @property {string} [cancelLabel] - Cancel button label (default: "Cancel")
 * @property {function} onConfirm - Handler for confirm action
 * @property {function} [onCancel] - Handler for cancel action
 * @property {string} [variant] - Variant ('default' | 'destructive')
 * @property {boolean} [loading] - Whether the confirm action is loading
 */

/**
 * Reusable Confirmation Dialog component for consistent confirmation dialogs.
 * @param {ConfirmDialogProps} props
 */
const ConfirmDialog = React.memo(({
  open,
  onOpenChange,
  title,
  description,
  confirmLabel = "Confirm",
  cancelLabel = "Cancel",
  onConfirm,
  onCancel,
  variant = 'default',
  loading = false
}) => {
  const isDestructive = variant === 'destructive';

  const handleConfirm = () => {
    if (onConfirm) {
      onConfirm();
    }
    if (!loading) {
      onOpenChange(false);
    }
  };

  const handleCancel = () => {
    if (onCancel) {
      onCancel();
    }
    onOpenChange(false);
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[425px]">
        <DialogHeader>
          <div className="flex items-center gap-3">
            {isDestructive && (
              <div className="w-10 h-10 rounded-full bg-red-100 flex items-center justify-center">
                <AlertTriangle className="w-5 h-5 text-red-600" />
              </div>
            )}
            <div>
              <DialogTitle className={isDestructive ? "text-red-900" : ""}>
                {title}
              </DialogTitle>
              {description && (
                <DialogDescription className="mt-2">
                  {description}
                </DialogDescription>
              )}
            </div>
          </div>
        </DialogHeader>
        <DialogFooter>
          <Button
            variant="outline"
            onClick={handleCancel}
            disabled={loading}
          >
            {cancelLabel}
          </Button>
          <Button
            variant={isDestructive ? "destructive" : "default"}
            onClick={handleConfirm}
            disabled={loading}
          >
            {loading ? "Processing..." : confirmLabel}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
});

ConfirmDialog.displayName = "ConfirmDialog";

export default ConfirmDialog;

