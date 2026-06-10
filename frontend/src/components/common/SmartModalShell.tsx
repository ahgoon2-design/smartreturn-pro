import { Modal } from "antd";
import type { ModalProps } from "antd";

export function SmartModalShell({ width = 560, maskClosable = false, destroyOnHidden = true, className, ...props }: ModalProps) {
  const modalClassName = ["smart-modal-shell", className].filter(Boolean).join(" ");
  return <Modal width={width} maskClosable={maskClosable} destroyOnHidden={destroyOnHidden} className={modalClassName} {...props} />;
}
