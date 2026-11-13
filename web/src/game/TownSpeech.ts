import Phaser from "phaser";

export type ConversationEvent = {
  id: number;
  tick: number;
  actor: string;
  type: string;
  payload: {
    listener?: string;
    message?: string;
    location?: string;
  };
};

type SpeechItem = {
  speaker: string;
  message: string;
  character: Phaser.GameObjects.Container;
};

export class TownSpeech {
  private scene: Phaser.Scene;
  private queue: SpeechItem[] = [];
  private active: Phaser.GameObjects.Container | null = null;
  private expiresAt = 0;
  private activeCharacter: Phaser.GameObjects.Container | null = null;
  private activeHeight = 0;

  constructor(scene: Phaser.Scene) {
    this.scene = scene;

    scene.events.on(
      Phaser.Scenes.Events.UPDATE,
      this.update,
      this,
    );

    scene.events.once(
      Phaser.Scenes.Events.SHUTDOWN,
      this.destroy,
      this,
    );
  }

  show(
    speaker: string,
    message: string,
    character: Phaser.GameObjects.Container,
  ) {
    if (!message.trim()) return;

    this.queue.push({
      speaker,
      message,
      character,
    });

    // Prevent an unlimited backlog if the API returns
    // messages faster than they can be displayed.
    if (this.queue.length > 12) {
      this.queue.splice(0, this.queue.length - 12);
    }

    if (!this.active) {
      this.showNext();
    }
  }

  private showNext() {
    if (this.active || this.queue.length === 0) return;

    const item = this.queue.shift()!;

    const text = this.scene.add.text(
      0,
      0,
      item.message,
      {
        fontFamily: "monospace",
        fontSize: "13px",
        color: "#243b2b",
        wordWrap: { width: 210 },
        align: "center",
      },
    ).setOrigin(0.5);

    const width = Math.min(
      240,
      Math.max(110, text.width + 24),
    );

    const height = text.height + 24;

    const background = this.scene.add.graphics();

    background.fillStyle(0xffffff, 0.97);
    background.fillRoundedRect(
      -width / 2,
      -height / 2,
      width,
      height,
      10,
    );

    background.lineStyle(2, 0x344b37);
    background.strokeRoundedRect(
      -width / 2,
      -height / 2,
      width,
      height,
      10,
    );

    this.active = this.scene.add.container(
      0,
      0,
      [background, text],
    );

    this.active.setDepth(1000);
    this.activeCharacter = item.character;
    this.activeHeight = height;

    // Allow enough time to read longer messages.
    const duration = Math.min(
      6500,
      Math.max(3000, item.message.length * 45),
    );

    this.expiresAt = this.scene.time.now + duration;

    this.positionBubble();
  }

  private positionBubble() {
    if (!this.active || !this.activeCharacter) return;

    const character = this.activeCharacter;

    // Keep the bubble inside the game canvas.
    const x = Phaser.Math.Clamp(
      character.x,
      130,
      830,
    );

    const y = Phaser.Math.Clamp(
      character.y - 105,
      this.activeHeight / 2 + 15,
      610 - this.activeHeight / 2,
    );

    this.active.setPosition(x, y);
  }

  private update() {
    if (this.active) {
      if (this.scene.time.now >= this.expiresAt) {
        this.active.destroy();
        this.active = null;
        this.activeCharacter = null;
      } else {
        this.positionBubble();
      }
    }

    if (!this.active) {
      this.showNext();
    }
  }

  destroy() {
    this.scene.events.off(
      Phaser.Scenes.Events.UPDATE,
      this.update,
      this,
    );

    this.active?.destroy();
    this.active = null;
    this.activeCharacter = null;
    this.queue = [];
  }
}
