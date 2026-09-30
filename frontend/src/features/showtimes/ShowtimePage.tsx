import { useParams } from "react-router";

export function ShowtimePage() {
  const { id } = useParams();
  return (
    <div className="py-16 text-center text-slate-400">
      Sơ đồ ghế của suất chiếu #{id} sẽ làm ở Bước 11 (WebSocket realtime).
    </div>
  );
}