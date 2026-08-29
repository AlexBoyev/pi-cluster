import "./ConfirmDialog.css";

interface Props {
  title: string;
  message: string;
  confirmLabel?: string;
  dangerous?: boolean;
  onConfirm: () => void;
  onCancel: () => void;
}

export default function ConfirmDialog({ title, message, confirmLabel = "Confirm", dangerous = false, onConfirm, onCancel }: Props) {
  return (
    <div className="cdlg-overlay" onClick={(e) => { if (e.target === e.currentTarget) onCancel(); }}>
      <div className="cdlg-box">
        <div className="cdlg-title">{title}</div>
        <div className="cdlg-message">{message}</div>
        <div className="cdlg-actions">
          <button className="cdlg-btn-cancel" onClick={onCancel}>Cancel</button>
          <button className={`cdlg-btn-confirm${dangerous ? " cdlg-btn-danger" : ""}`} onClick={onConfirm}>
            {confirmLabel}
          </button>
        </div>
      </div>
    </div>
  );
}
