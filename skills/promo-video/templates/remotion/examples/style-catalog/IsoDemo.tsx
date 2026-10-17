import React, { useEffect, useState } from "react";
import { AbsoluteFill, cancelRender, continueRender, delayRender, staticFile, useCurrentFrame } from "remotion";
import { Bars, Billboard, House, ISO_ELEV, IsoCanvas, IsoCard, IsoTile, Library, Mark3D, Tree, useCanvasTexture, scatter } from "../cinematic/iso";
import { fam } from "../cinematic/type";
import { step } from "../cinematic/spring";

/** 03 · 等轴 2.5D — "YouWare Town": one prompt tile, four districts grow on the beat, the mark lands on the tower. 300 frames. */
export const ISO_LEN = 330;
const SANS = fam("Manrope");
const MONO = fam("Geist Mono");
const N = 7; // tiles from -N .. N-1

const useSvgText = (url: string) => {
  const [txt, setTxt] = useState<string | null>(null);
  const [h] = useState(() => delayRender("mark svg"));
  useEffect(() => {
    fetch(url)
      .then((r) => r.text())
      .then((s) => {
        setTxt(s);
        continueRender(h);
      })
      .catch((e) => cancelRender(e));
  }, [h, url]);
  return txt;
};

type District = "web" | "slides" | "sheets" | "reports" | "plaza" | "road";
const districtOf = (x: number, z: number): District => {
  if ((x === -1 || x === 0) && (z === -1 || z === 0)) return "plaza";
  if (x === -1 || x === 0 || z === -1 || z === 0) return "road";
  if (x < 0 && z > 0) return "web";
  if (x > 0 && z < 0) return "slides";
  if (x < 0 && z < 0) return "sheets";
  return "reports";
};
const TILE: Record<District, string> = { plaza: "#FFFFFF", road: "#E4DDCF", web: "#F3E7DC", slides: "#E9E4F5", sheets: "#E6EDD2", reports: "#DDE7F3" };
const START: Record<District, number> = { plaza: 0, road: 20, web: 58, slides: 88, sheets: 118, reports: 148 };

const PromptTile: React.FC<{ t: number }> = ({ t }) => {
  const tex = useCanvasTexture(
    512,
    512,
    (c) => {
      c.fillStyle = "#FFFFFF";
      c.fillRect(0, 0, 512, 512);
      c.fillStyle = "#F1ECE2";
      c.beginPath();
      c.roundRect(40, 196, 432, 120, 60);
      c.fill();
      c.fillStyle = "#151513";
      c.beginPath();
      c.arc(412, 256, 38, 0, Math.PI * 2);
      c.fill();
      c.strokeStyle = "#FFFFFF";
      c.lineWidth = 9;
      c.lineCap = "round";
      c.beginPath();
      c.moveTo(412, 276);
      c.lineTo(412, 236);
      c.moveTo(396, 252);
      c.lineTo(412, 236);
      c.lineTo(428, 252);
      c.stroke();
      c.fillStyle = "rgba(21,21,19,0.55)";
      c.fillRect(80, 246, 220, 20);
    },
    [],
  );
  const pulse = Math.max(0, Math.min(1, (t - 14) / 24));
  return (
    <group>
      <mesh position={[-0.5, 0.02, -0.5]} receiveShadow castShadow>
        <boxGeometry args={[1.96, 0.34, 1.96]} />
        <meshStandardMaterial attach="material-0" color="#F4F0E8" />
        <meshStandardMaterial attach="material-1" color="#F4F0E8" />
        <meshStandardMaterial attach="material-2" map={tex} />
        <meshStandardMaterial attach="material-3" color="#F4F0E8" />
        <meshStandardMaterial attach="material-4" color="#F4F0E8" />
        <meshStandardMaterial attach="material-5" color="#F4F0E8" />
      </mesh>
      {pulse > 0 && pulse < 1 && (
        <mesh position={[-0.5, 0.2, -0.5]} rotation={[-Math.PI / 2, 0, 0]}>
          <ringGeometry args={[1 + pulse * 7, 1.12 + pulse * 7, 64]} />
          <meshBasicMaterial color="#CFE3A0" transparent opacity={0.8 * (1 - pulse)} toneMapped={false} />
        </mesh>
      )}
    </group>
  );
};

export const IsoDemo: React.FC<{ t?: number }> = ({ t: tProp }) => {
  const frame = useCurrentFrame();
  const t = tProp ?? frame;
  const svg = useSvgText(staticFile("brand/mark.svg"));
  const wide = step(Math.max(0, (t - 10) / 30), { w: 2 * Math.PI * 0.55, z: 0.95 });
  const push = step(Math.max(0, (t - 214) / 30), { w: 2 * Math.PI * 0.8, z: 0.9 });
  const zoom = 250 + (74 - 250) * wide + 26 * push;
  const yaw = -0.3 + 0.36 * Math.min(1, t / 300);
  const tiles: [number, number][] = [];
  for (let x = -N; x < N; x++) for (let z = -N; z < N; z++) tiles.push([x, z]);
  const dist = (x: number, z: number) => Math.hypot(x + 0.5, z + 0.5);
  const lot = (d: District) => tiles.filter(([x, z]) => districtOf(x, z) === d && (x + z) % 2 === 0 && Math.abs(x + 0.5) < N - 1 && Math.abs(z + 0.5) < N - 1);
  const trees = scatter(18, "tree", [-N + 0.5, -N + 0.5, N - 1.5, N - 1.5]).filter(([x, z]) => Math.abs(x + 0.5) > 1.6 && Math.abs(z + 0.5) > 1.6);
  const markDrop = step(Math.max(0, (t - 222) / 30), { w: 2 * Math.PI * 1.8, z: 0.45 });
  const towerH = 2.2 * step(Math.max(0, (t - 196) / 30), { w: 2 * Math.PI * 1.6, z: 0.6 });
  return (
    <AbsoluteFill style={{ background: "radial-gradient(ellipse at 50% 42%, #FBF8F1 0%, #EDE9F5 55%, #D9D3E8 100%)" }}>
      <IsoCanvas zoom={zoom} yaw={yaw} target={[-0.5, 0.35 + 0.9 * push, -0.5]}>
        {/* slab */}
        <mesh position={[-0.5, -0.45, -0.5]} receiveShadow scale={[1, Math.min(1, t / 8), 1]}>
          <boxGeometry args={[2 * N + 0.5, 0.6, 2 * N + 0.5]} />
          <meshStandardMaterial color="#CFC6B4" roughness={0.9} />
        </mesh>
        <PromptTile t={t} />
        {tiles.map(([x, z]) => {
          const d = districtOf(x, z);
          if (d === "plaza") return null;
          const at = (d === "road" ? START.road : Math.min(START[d] - 10, 26)) + dist(x, z) * 2.6;
          const checker = d === "sheets" && (x + z) % 2 !== 0 ? "#CFE3A0" : TILE[d];
          return <IsoTile key={`${x},${z}`} t={t} at={at} x={x} z={z} color={checker} />;
        })}
        {lot("web").map(([x, z], i) => (
          <House key={`h${x}${z}`} t={t} at={START.web + i * 2} x={x} z={z} roof={["#EE8C6C", "#F36440", "#FFD15C"][i % 3]} rot={(i % 2) * Math.PI / 2} h={0.45 + 0.2 * ((i * 7) % 3)} />
        ))}
        {lot("slides").map(([x, z], i) => (
          <Billboard key={`b${x}${z}`} t={t} at={START.slides + i * 2} x={x} z={z} accent={["#7D6BC1", "#EE8C6C", "#2556B6"][i % 3]} photo={["#FFD15C", "#CFE3A0", "#FFFFFF"][i % 3]} rot={Math.PI / 4} />
        ))}
        {lot("sheets").map(([x, z], i) => (i % 2 === 0 ? <Bars key={`s${x}${z}`} t={t} at={START.sheets + i * 2} x={x} z={z} heights={[0.4 + (i % 3) * 0.2, 0.8, 0.55, 1.1 - (i % 2) * 0.3]} /> : null))}
        {[[5, 1], [1, 5]].map(([x, z], i) => (
          <Library key={`lib${i}`} t={t} at={START.reports + 4 + i * 6} x={x} z={z} floors={6} />
        ))}
        {lot("reports").filter(([x, z]) => !((x === 5 && z === 1) || (x === 1 && z === 5))).map(([x, z], i) => (false ? null : <House key={`r${x}${z}`} t={t} at={START.reports + i * 2} x={x} z={z} wall="#FFFFFF" roof="#2556B6" h={0.4} />))}
        {trees.map(([x, z], i) => (
          <Tree key={`t${i}`} t={t} at={60 + i * 6} x={Math.round(x)} z={Math.round(z)} color={i % 3 ? "#7D8F57" : "#BAC78D"} s={0.8 + 0.3 * ((i * 5) % 3) / 2} />
        ))}
        {/* the tower + the mark */}
        {towerH > 0.01 && (
          <group position={[-0.5, 0.19, -0.5]}>
            <mesh position={[0, towerH / 2, 0]} castShadow>
              <cylinderGeometry args={[0.42, 0.52, Math.max(0.01, towerH), 40]} />
              <meshStandardMaterial color="#F5F0E6" roughness={0.55} />
            </mesh>
            <mesh position={[0, towerH * 0.62, 0]} castShadow>
              <torusGeometry args={[0.47, 0.05, 12, 48]} />
              <meshStandardMaterial color="#CFE3A0" roughness={0.5} />
            </mesh>
            {svg && markDrop > 0.001 && (
              <group position={[0, towerH + 0.95 + (1 - markDrop) * 3.2, 0]} rotation={[0, Math.PI / 4 + yaw + 0.12 * Math.sin((t - 222) / 30 * 1.6), 0]}>
                <group rotation={[-ISO_ELEV * 0.55, 0, 0]}>
                <Mark3D svg={svg} size={1.8} depth={0.16} color="#151513" />
                </group>
              </group>
            )}
          </group>
        )}
        {/* district cards */}
        <IsoCard t={t} at={START.web + 16} position={[-4.5, 2.1, 3.5]} title="Websites" sub={`HOUSES · ${lot("web").length}`} accent="#EE8C6C" family={SANS} mono={MONO} w={2.9} />
        <IsoCard t={t} at={START.slides + 16} position={[3.5, 2.3, -4.5]} title="Slides" sub={`BILLBOARDS · ${lot("slides").length}`} accent="#7D6BC1" family={SANS} mono={MONO} w={2.9} />
        <IsoCard t={t} at={START.sheets + 16} position={[-4.5, 2.1, -4.5]} title="Sheets" sub="FIELDS · CHARTS" accent="#7D8F57" family={SANS} mono={MONO} w={2.9} />
        <IsoCard t={t} at={START.reports + 16} position={[3.5, 2.3, 3.5]} title="Reports" sub="LIBRARY · STACKS" accent="#2556B6" family={SANS} mono={MONO} w={2.9} />
      </IsoCanvas>
      <div style={{ position: "absolute", left: 64, top: 52, fontFamily: MONO, fontSize: 20, letterSpacing: "0.22em", color: "rgba(21,21,19,0.6)" }}>YOUWARE TOWN</div>
      <div style={{ position: "absolute", right: 64, bottom: 52, fontFamily: MONO, fontSize: 20, letterSpacing: "0.22em", color: "rgba(21,21,19,0.6)" }}>1 PROMPT · 4 DISTRICTS</div>
    </AbsoluteFill>
  );
};
