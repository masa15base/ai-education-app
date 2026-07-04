import { Link } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";

type Props = {
  /** 画面ごとの短い見出し */
  title?: string;
  /** 補足（1〜2文） */
  description: string;
  className?: string;
};

/**
 * 未ログイン時に共通表示する案内（A+C: 体験の導線を揃える）
 */
export function LoggedOutCTA({
  title = "ログインすると便利だよ",
  description,
  className = "",
}: Props) {
  return (
    <Card
      className={`border-dashed border-2 border-sky-soft/50 bg-white/80 p-4 text-left ${className}`}
    >
      <p className="font-semibold text-navy-dark text-sm mb-1">{title}</p>
      <p className="text-xs text-gray-600 mb-3 leading-relaxed">{description}</p>
      <div className="flex flex-wrap gap-2">
        <Button size="sm" className="kid-button" asChild>
          <Link to="/login">ログインへ</Link>
        </Button>
        <Button size="sm" variant="outline" asChild>
          <Link to="/">ホームへ</Link>
        </Button>
      </div>
    </Card>
  );
}
