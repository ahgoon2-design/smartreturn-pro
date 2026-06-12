/**
 * SmartReturn Pro 화면 도움말 공통 타입.
 * 도움말 본문은 SmartReturn Pro 전용이며 다른 SmartReturn 플랫폼과 공용화하지 않는다.
 * 구조(타입)만 추후 다른 플랫폼에서 복사해 쓸 수 있다.
 */

/** 도움말을 보는 대상. internal=내부 운영자, client=고객사 사용자, both=둘 다. */
export type HelpAudience = "internal" | "client" | "both";

export interface HelpSection {
  /** 섹션 제목. 예: "이 화면은 뭐 하는 화면인가요?" */
  heading: string;
  /** 사용자용 쉬운 한글 문장 목록. 개발자 용어는 괄호 설명을 붙인다. */
  items: string[];
}

export interface ScreenHelpEntry {
  /** 화면 식별자. 도움말 버튼에서 이 키로 조회한다. */
  screenKey: string;
  /** 화면 route. 아직 화면이 없으면 비워두고 draft로 표시한다. */
  route?: string;
  title: string;
  /** 한 줄 요약. 화면 상단/도움말 첫 줄에 쓴다. */
  summary: string;
  audience: HelpAudience;
  /** 화면/route가 아직 확정되지 않은 초안 여부. */
  draft?: boolean;
  sections: HelpSection[];
  /** 실수하기 쉬운 위험 안내. 빨간/노란 강조로 표시한다. */
  warnings: string[];
  /** 관련 화면 screenKey 목록. */
  relatedScreens: string[];
}

export type ScreenHelpRegistry = Record<string, ScreenHelpEntry>;
