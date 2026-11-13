import Phaser from "phaser";

const WIDTH = 960;
const HEIGHT = 640;

export class TownScene extends Phaser.Scene {
  constructor() {
    super("TownScene");
  }

  create() {
    const graphics = this.add.graphics();

    // Grass background
    graphics.fillStyle(0x78a65c);
    graphics.fillRect(0, 0, WIDTH, HEIGHT);

    // Grass texture
    for (let y = 12; y < HEIGHT; y += 24) {
      for (let x = 12; x < WIDTH; x += 24) {
        const shade = (x * 17 + y * 31) % 3;
        graphics.fillStyle(
          shade === 0 ? 0x83b367 : 0x6e9a53,
          0.55,
        );
        graphics.fillRect(x, y, 5, 5);
      }
    }

    // Town roads
    graphics.fillStyle(0xd7bd8d);
    graphics.fillRect(0, 288, WIDTH, 72);
    graphics.fillRect(444, 0, 72, HEIGHT);

    // Road edging
    graphics.lineStyle(3, 0xbda477);
    graphics.strokeRect(0, 288, WIDTH, 72);
    graphics.strokeRect(444, 0, 72, HEIGHT);

    // Buildings
    this.drawBuilding(175, 150, 0xc97655, "BAKERY", "🥐");
    this.drawBuilding(785, 150, 0x668fc5, "SCHOOL", "📚");
    this.drawBuilding(175, 490, 0xc27cab, "SHOP", "🛍");
    this.drawSquare(785, 490);

    // Trees around the village
    const trees = [
      [40, 60], [85, 80], [360, 55], [585, 75],
      [910, 65], [40, 245], [915, 250],
      [65, 405], [355, 430], [590, 420],
      [925, 405], [40, 590], [365, 585],
      [585, 590], [920, 585],
    ];

    for (const [x, y] of trees) {
      this.drawTree(x, y);
    }

    // Game title
    this.add.text(480, 25, "LIVING AI TOWN", {
      fontFamily: "monospace",
      fontSize: "24px",
      color: "#ffffff",
      fontStyle: "bold",
      stroke: "#27462b",
      strokeThickness: 5,
    }).setOrigin(0.5);

    // Camera
    this.cameras.main.setBounds(0, 0, WIDTH, HEIGHT);
    this.cameras.main.setZoom(1);
  }

  private drawBuilding(
    x: number,
    y: number,
    roofColor: number,
    label: string,
    symbol: string,
  ) {
    const g = this.add.graphics();

    // Shadow
    g.fillStyle(0x304b30, 0.3);
    g.fillRoundedRect(x - 86, y - 52, 180, 142, 8);

    // Building walls
    g.fillStyle(0xf0dbac);
    g.fillRect(x - 80, y - 45, 160, 125);

    // Roof
    g.fillStyle(roofColor);
    g.fillRect(x - 92, y - 60, 184, 55);

    // Roof trim
    g.fillStyle(0x604b43);
    g.fillRect(x - 92, y - 8, 184, 7);

    // Door
    g.fillStyle(0x76533c);
    g.fillRect(x - 16, y + 30, 32, 50);

    // Windows
    g.fillStyle(0x91c5cf);
    g.fillRect(x - 62, y + 12, 30, 30);
    g.fillRect(x + 32, y + 12, 30, 30);

    this.add.text(x, y - 34, symbol, {
      fontSize: "27px",
    }).setOrigin(0.5);

    this.add.text(x, y + 101, label, {
      fontFamily: "monospace",
      fontSize: "17px",
      fontStyle: "bold",
      color: "#203b27",
    }).setOrigin(0.5);
  }

  private drawTree(x: number, y: number) {
    const g = this.add.graphics();

    g.fillStyle(0x5a422e);
    g.fillRect(x - 6, y, 12, 28);

    g.fillStyle(0x315f37);
    g.fillCircle(x, y - 10, 25);

    g.fillStyle(0x44844a);
    g.fillCircle(x - 8, y - 17, 20);

    g.fillStyle(0x589d53);
    g.fillCircle(x + 8, y - 22, 15);
  }

  private drawSquare(x: number, y: number) {
    const g = this.add.graphics();

    g.fillStyle(0xd4c4a0);
    g.fillCircle(x, y, 100);

    g.fillStyle(0xf2e6ce);
    g.fillCircle(x, y, 65);

    g.fillStyle(0x7db9c9);
    g.fillCircle(x, y, 42);

    g.fillStyle(0x4b91ad);
    g.fillCircle(x, y, 25);

    g.fillStyle(0xe4e8dc);
    g.fillRect(x - 9, y - 45, 18, 48);

    this.add.text(x, y + 115, "TOWN SQUARE", {
      fontFamily: "monospace",
      fontSize: "17px",
      fontStyle: "bold",
      color: "#203b27",
    }).setOrigin(0.5);
  }
}
