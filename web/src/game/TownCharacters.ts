import Phaser from "phaser";

export type Movement = {
  from: string;
  to: string;
  start_tick: number;
  duration_ticks: number;
};

export type TownCharacter = {
  name: string;
  profession: string;
  location: string;
  activity: string;
  movement: Movement | null;
};

export type TownWorld = {
  tick: number;
  state: {
    characters: Record<string, TownCharacter>;
  };
};

type Point = { x: number; y: number };
type Direction = "up" | "down" | "left" | "right";

const LOCATIONS: Record<string, Point> = {
  bakery: { x: 175, y: 245 },
  school: { x: 785, y: 245 },
  shop: { x: 175, y: 580 },
  square: { x: 785, y: 585 },
};

const COLORS: Record<string, number> = {
  emma: 0xf2a23a,
  noah: 0x5b9ee7,
  sophia: 0xe877ad,
};

type SpriteEntry = {
  container: Phaser.GameObjects.Container;
  body: Phaser.GameObjects.Graphics;
  label: Phaser.GameObjects.Text;
  color: number;
  position: Point;
  target: Point;
  direction: Direction;
  moving: boolean;
  walkTime: number;
};

function roadRoute(from: string, to: string): Point[] {
  const start = LOCATIONS[from];
  const end = LOCATIONS[to];

  if (!start || !end) return [];

  if (from === to) return [start];

  const centerX = 480;
  const centerY = 324;

  const points: Point[] = [
    start,
    { x: start.x, y: centerY },
    { x: centerX, y: centerY },
    { x: end.x, y: centerY },
    end,
  ];

  return points.filter(
    (point, index) =>
      index === 0 ||
      point.x !== points[index - 1].x ||
      point.y !== points[index - 1].y,
  );
}

function interpolateRoute(route: Point[], progress: number): Point {
  if (route.length === 0) return { x: 480, y: 324 };
  if (route.length === 1) return route[0];

  const lengths = route.slice(1).map((point, index) =>
    Phaser.Math.Distance.Between(
      route[index].x,
      route[index].y,
      point.x,
      point.y,
    ),
  );

  const total = lengths.reduce((sum, length) => sum + length, 0);
  let remaining = Phaser.Math.Clamp(progress, 0, 1) * total;

  for (let index = 0; index < lengths.length; index++) {
    if (remaining <= lengths[index]) {
      const ratio =
        lengths[index] === 0 ? 1 : remaining / lengths[index];

      return {
        x: Phaser.Math.Linear(route[index].x, route[index + 1].x, ratio),
        y: Phaser.Math.Linear(route[index].y, route[index + 1].y, ratio),
      };
    }

    remaining -= lengths[index];
  }

  return route[route.length - 1];
}

export function characterPosition(
  character: TownCharacter,
  tick: number,
): Point {
  if (!character.movement) {
    const location = LOCATIONS[character.location];
    return location ? { ...location } : { x: 480, y: 324 };
  }

  const movement = character.movement;
  const progress =
    (tick - movement.start_tick) /
    Math.max(1, movement.duration_ticks);

  return interpolateRoute(
    roadRoute(movement.from, movement.to),
    progress,
  );
}

function directionBetween(a: Point, b: Point): Direction {
  const dx = b.x - a.x;
  const dy = b.y - a.y;

  if (Math.abs(dx) > Math.abs(dy)) {
    return dx >= 0 ? "right" : "left";
  }

  return dy >= 0 ? "down" : "up";
}

function drawCharacter(
  graphics: Phaser.GameObjects.Graphics,
  color: number,
  direction: Direction,
  walking: boolean,
  walkTime: number,
) {
  graphics.clear();

  const stride = walking ? Math.round(Math.sin(walkTime * 0.014) * 4) : 0;

  graphics.fillStyle(0x243b2b, 0.3);
  graphics.fillEllipse(0, 7, 26, 8);

  graphics.fillStyle(0x374151);
  graphics.fillRect(-8, -3 + stride, 6, 12);
  graphics.fillRect(2, -3 - stride, 6, 12);

  graphics.fillStyle(color);
  graphics.fillRect(-11, -23, 22, 24);

  graphics.fillStyle(0xf5c9a5);
  graphics.fillRect(-9, -40, 18, 18);

  graphics.fillStyle(0x51372b);
  graphics.fillRect(-11, -43, 22, 7);

  if (direction !== "up") {
    graphics.fillStyle(0x263238);

    if (direction === "left") {
      graphics.fillRect(-7, -31, 3, 3);
    } else if (direction === "right") {
      graphics.fillRect(4, -31, 3, 3);
    } else {
      graphics.fillRect(-5, -31, 3, 3);
      graphics.fillRect(3, -31, 3, 3);
    }
  }
}

export class TownCharacters {
  private scene: Phaser.Scene;
  private sprites = new Map<string, SpriteEntry>();

  constructor(scene: Phaser.Scene) {
    this.scene = scene;

    this.scene.events.on(
      Phaser.Scenes.Events.UPDATE,
      this.onFrame,
      this,
    );

    this.scene.events.once(
      Phaser.Scenes.Events.SHUTDOWN,
      this.destroy,
      this,
    );
  }

  update(world: TownWorld) {
    const ids = new Set(Object.keys(world.state.characters));

    const characters = Object.entries(world.state.characters);

    // Group idle characters by location for visual spacing.
    // This never changes the authoritative world state.
    const idleGroups = new Map<string, string[]>();

    for (const [id, character] of characters) {
      if (character.movement !== null) continue;

      const group = idleGroups.get(character.location) ?? [];
      group.push(id);
      idleGroups.set(character.location, group);
    }

    for (const group of idleGroups.values()) {
      group.sort();
    }

    for (const [id, character] of characters) {
      const target = characterPosition(character, world.tick);

      // Visual-only lane separation for characters in motion.
      // Preserve the authoritative route and simulation state.
      if (character.movement !== null) {
        const laneOffset: Record<string, number> = {
          emma: -44,
          noah: 0,
          sophia: 44,
        };

        target.x += laneOffset[id] ?? 0;
      }

      if (character.movement === null) {
        const group = idleGroups.get(character.location) ?? [];
        const index = group.indexOf(id);

        if (group.length > 1 && index >= 0) {
          const spacing = 48;
          target.x += (index - (group.length - 1) / 2) * spacing;
        }
      }

      let entry = this.sprites.get(id);

      if (!entry) {
        entry = this.createCharacter(
          id,
          character.name,
          target,
        );
        this.sprites.set(id, entry);
      }

      entry.target = target;
      entry.moving =
        Math.hypot(
          target.x - entry.position.x,
          target.y - entry.position.y,
        ) > 0.5;

      entry.label.setText(character.name);
    }

    for (const [id, entry] of this.sprites) {
      if (!ids.has(id)) {
        entry.container.destroy();
        this.sprites.delete(id);
      }
    }
  }

  private onFrame(_time: number, delta: number) {
    for (const entry of this.sprites.values()) {
      const distance = Math.hypot(
        entry.target.x - entry.position.x,
        entry.target.y - entry.position.y,
      );

      if (distance > 0.5) {
        const before = { ...entry.position };

        // Move smoothly toward the confirmed target at a fixed speed.
        // Avoid asymptotic interpolation that never quite arrives.
        const speed = 240;
        const step = Math.min(distance, speed * delta / 1000);
        const ratio = distance === 0 ? 1 : step / distance;

        entry.position.x +=
          (entry.target.x - entry.position.x) * ratio;
        entry.position.y +=
          (entry.target.y - entry.position.y) * ratio;

        entry.direction = directionBetween(before, entry.position);
        entry.moving = true;
        entry.walkTime += delta;
      } else {
        entry.position = { ...entry.target };
        entry.moving = false;
        entry.walkTime = 0;
      }

      entry.container.setPosition(
        entry.position.x,
        entry.position.y,
      );

      drawCharacter(
        entry.body,
        entry.color,
        entry.direction,
        entry.moving,
        entry.walkTime,
      );
    }
  }

  private createCharacter(
    id: string,
    name: string,
    position: Point,
  ): SpriteEntry {
    const container = this.scene.add.container(
      position.x,
      position.y,
    );

    const body = this.scene.add.graphics();

    const label = this.scene.add.text(0, -59, name, {
      fontFamily: "monospace",
      fontSize: "14px",
      fontStyle: "bold",
      color: "#ffffff",
      backgroundColor: "#243b2bcc",
      padding: { x: 5, y: 3 },
    }).setOrigin(0.5);

    container.add([body, label]);
    container.setDepth(20);
    container.setSize(38, 70);

    container.setInteractive(
      new Phaser.Geom.Rectangle(-30, -72, 60, 90),
      Phaser.Geom.Rectangle.Contains,
    );

    container.on("pointerdown", () => {
      this.scene.game.events.emit("character-selected", id);
    });

    return {
      container,
      body,
      label,
      color: COLORS[id] ?? 0x9ca3af,
      position: { ...position },
      target: { ...position },
      direction: "down",
      moving: false,
      walkTime: 0,
    };
  }

  getCharacterContainer(id: string) {
    return this.sprites.get(id)?.container;
  }

  destroy() {
    this.scene.events.off(
      Phaser.Scenes.Events.UPDATE,
      this.onFrame,
      this,
    );

    for (const entry of this.sprites.values()) {
      entry.container.destroy();
    }

    this.sprites.clear();
  }
}
