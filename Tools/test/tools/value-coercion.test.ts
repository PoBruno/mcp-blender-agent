/**
 * S6-18 — coerce_value boundary tests.
 *
 * Some MCP clients stringify untyped fields (Zod z.unknown / z.record(z.unknown)),
 * so a float arrives as "0.42" and a color as "[0.8, 0.1, 0.1, 1]". The addon
 * recovers them at the shader/geo/modifier/light boundaries via coerce_value.
 *
 * These tests pin that contract — if anyone removes the coercion, a typed
 * client gets RNA TypeError and these tests fail loudly.
 */

import { afterAll, beforeAll, describe, expect, it } from "vitest";

import { blenderPost, startBlender, stopBlender } from "../bootstrap.js";

describe("value coercion at boundaries (S6-18)", () => {
  beforeAll(async () => {
    await startBlender();
    await blenderPost("/file/new", { empty: true });
  }, 90_000);

  afterAll(async () => {
    await stopBlender();
  });

  describe("shader_node_set_input_value (Principled BSDF)", () => {
    it("accepts a native float on Roughness", async () => {
      await blenderPost("/material/create", { name: "M_Coerce" });
      // a freshly created material has use_nodes on, with a Principled BSDF
      const r = await blenderPost("/shader_node/set_input_value", {
        materialName: "M_Coerce",
        nodeName: "Principled BSDF",
        socketName: "Roughness",
        value: 0.42,
      });
      expect(r.ok).toBe(true);
    });

    it("accepts a stringified float on Roughness", async () => {
      const r = await blenderPost("/shader_node/set_input_value", {
        materialName: "M_Coerce",
        nodeName: "Principled BSDF",
        socketName: "Roughness",
        value: "0.16",
      });
      expect(r.ok).toBe(true);
    });

    it("accepts a stringified color array on Base Color", async () => {
      const r = await blenderPost("/shader_node/set_input_value", {
        materialName: "M_Coerce",
        nodeName: "Principled BSDF",
        socketName: "Base Color",
        value: "[0.8, 0.1, 0.1, 1.0]",
      });
      expect(r.ok).toBe(true);
    });

    it("accepts a native color array on Base Color", async () => {
      const r = await blenderPost("/shader_node/set_input_value", {
        materialName: "M_Coerce",
        nodeName: "Principled BSDF",
        socketName: "Base Color",
        value: [0.1, 0.8, 0.2, 1.0],
      });
      expect(r.ok).toBe(true);
    });

    it("accepts a stringified vector on a Mapping node", async () => {
      const add = await blenderPost<{ nodeName: string }>("/shader_node/add", {
        materialName: "M_Coerce",
        type: "ShaderNodeMapping",
        name: "MapCoerce",
      });
      expect(add.ok).toBe(true);
      const r = await blenderPost("/shader_node/set_input_value", {
        materialName: "M_Coerce",
        nodeName: add.data!.nodeName,
        socketName: "Scale",
        value: "[2.0, 2.0, 2.0]",
      });
      expect(r.ok).toBe(true);
    });
  });

  describe("light_set_property", () => {
    it("accepts stringified float for energy", async () => {
      await blenderPost("/light/create", { type: "POINT", name: "L_Coerce" });
      const r = await blenderPost("/light/set_property", {
        objectName: "L_Coerce",
        properties: { energy: "250.5" },
      });
      expect(r.ok).toBe(true);
    });

    it("accepts stringified color array", async () => {
      const r = await blenderPost("/light/set_property", {
        objectName: "L_Coerce",
        properties: { color: "[1.0, 0.5, 0.2]" },
      });
      expect(r.ok).toBe(true);
    });
  });

  describe("modifier_set_property", () => {
    it("accepts stringified int on Subdivision levels", async () => {
      await blenderPost("/object/create", { type: "CUBE", name: "C_Coerce" });
      await blenderPost("/modifier/add", {
        objectName: "C_Coerce",
        type: "SUBSURF",
        name: "Sub",
      });
      const r = await blenderPost("/modifier/set_property", {
        objectName: "C_Coerce",
        modifierName: "Sub",
        properties: { levels: "2" },
      });
      expect(r.ok).toBe(true);
    });

    it("accepts stringified float on Bevel width", async () => {
      await blenderPost("/modifier/add", {
        objectName: "C_Coerce",
        type: "BEVEL",
        name: "Bvl",
      });
      const r = await blenderPost("/modifier/set_property", {
        objectName: "C_Coerce",
        modifierName: "Bvl",
        properties: { width: "0.05" },
      });
      expect(r.ok).toBe(true);
    });
  });

  describe("keyframe_bone_pose default channel", () => {
    it("picks rotation_euler when bone.rotation_mode is XYZ", async () => {
      await blenderPost("/armature/create", { name: "ArmCoerce" });
      const ba = await blenderPost<{ boneName: string }>("/bone/add", {
        armatureObjectName: "ArmCoerce",
        name: "B0",
        head: [0, 0, 0],
        tail: [0, 0, 1],
      });
      expect(ba.ok).toBe(true);
      // Switch the pose bone to euler so the default channel logic kicks in.
      await blenderPost("/bone/set_pose_transform", {
        armatureObjectName: "ArmCoerce",
        boneName: "B0",
        rotationMode: "XYZ",
        rotationEuler: [0.2, 0, 0],
      });
      await blenderPost("/action/create", { name: "ACoerce" });
      await blenderPost("/action/assign_to_object", {
        objectName: "ArmCoerce",
        actionName: "ACoerce",
      });
      const k = await blenderPost<{ insertedChannels: string[] }>("/keyframe/bone_pose", {
        armatureObjectName: "ArmCoerce",
        boneName: "B0",
        frame: 1,
      });
      expect(k.ok).toBe(true);
      expect(k.data!.insertedChannels).toContain("rotation_euler");
      expect(k.data!.insertedChannels).not.toContain("rotation_quaternion");
    });

    it("picks rotation_quaternion by default", async () => {
      const ba = await blenderPost<{ boneName: string }>("/bone/add", {
        armatureObjectName: "ArmCoerce",
        name: "B1",
        head: [0, 0.5, 0],
        tail: [0, 0.5, 1],
      });
      expect(ba.ok).toBe(true);
      const k = await blenderPost<{ insertedChannels: string[] }>("/keyframe/bone_pose", {
        armatureObjectName: "ArmCoerce",
        boneName: "B1",
        frame: 1,
      });
      expect(k.ok).toBe(true);
      expect(k.data!.insertedChannels).toContain("rotation_quaternion");
    });
  });
});
