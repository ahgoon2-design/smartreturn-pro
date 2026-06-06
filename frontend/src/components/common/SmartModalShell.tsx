import { Modal } from "antd";
import type { ModalProps } from "antd";

export function SmartModalShell({ width = 560, maskClosable = false, destroyOnHidden = true, ...props }: ModalProps) {
  return <Modal width={width} maskClosable={maskClosable} destroyOnHidden={destroyOnHidden} {...props} />;
}
