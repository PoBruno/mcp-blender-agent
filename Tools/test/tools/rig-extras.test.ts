import { afterAll, beforeAll, describe, expect, it } from "vitest";

import { blenderPost, startBlender, stopBlender } from "../bootstrap.js";

describe("rig extras: bone set_parent/delete, vertex_group, shape_key, socket, constraints", () => {
  beforeAll(async () => {
    await startBlender();
    await blenderPost("/armature/create", { name: "Rig" });
    await blenderPost("/bone/add", {
      armatureObjectName: "Rig",
      name: "Root",
      head: [0, 0, 0],
      tail: [0, 0, 1],
    });
    await blenderPost("/bone/add", {
      armatureObjectName: "Rig",
      name: "Spine_01",
      head: [0, 0, 1],
      tail: [0, 0, 2],
    });
    await blenderPost("/bone/add", {
      armatureObjectName: "Rig",
      name: "ToDelete",
      head: [1, 0, 0],
      tail: [1, 0, 1],
    });
    await blenderPost("/object/create", { type: "CUBE", name: "SkinMesh" });
    await blenderPost("/object/create", { type: "CUBE", name: "SocketParent" });
  }, 90_000);

  afterAll(async () => {
    await stopBlender();
  });

  it("re-parents a bone", async () => {
    const res = await blenderPost<{ parent: string }>("/bone/set_parent", {
      armatureObjectName: "Rig",
      boneName: "Spine_01",
      parentName: "Root",
      useConnect: true,
    });
    expect(res.ok).toBe(true);
    expect(res.data?.parent).toBe("Root");
  });

  it("rejects missing parent with BONE_NOT_FOUND", async () => {
    const res = await blenderPost("/bone/set_parent", {
      armatureObjectName: "Rig",
      boneName: "Spine_01",
      parentName: "NoSuchBone",
    });
    expect(res.ok).toBe(false);
    expect(res.errorCode).toBe("BONE_NOT_FOUND");
  });

  it("deletes a bone", async () => {
    const res = await blenderPost("/bone/delete", {
      armatureObjectName: "Rig",
      boneName: "ToDelete",
    });
    expect(res.ok).toBe(true);
  });

  it("flips show_in_front on the armature", async () => {
    const res = await blenderPost<{ showInFront: boolean }>(
      "/armature/show_in_front",
      { armatureObjectName: "Rig", show: true },
    );
    expect(res.ok).toBe(true);
    expect(res.data?.showInFront).toBe(true);
  });

  it("creates a vertex group, assigns vertices, and deletes it", async () => {
    const create = await blenderPost<{ created: boolean }>("/vertex_group/create", {
      objectName: "SkinMesh",
      name: "Grp",
    });
    expect(create.ok).toBe(true);
    expect(create.data?.created).toBe(true);

    const assign = await blenderPost<{ assignedCount: number }>(
      "/vertex_group/assign_vertices",
      {
        objectName: "SkinMesh",
        vertexGroupName: "Grp",
        vertexIndices: [0, 1, 2, 3],
        weight: 0.75,
      },
    );
    expect(assign.ok).toBe(true);
    expect(assign.data?.assignedCount).toBe(4);

    const del = await blenderPost("/vertex_group/delete", {
      objectName: "SkinMesh",
      vertexGroupName: "Grp",
    });
    expect(del.ok).toBe(true);
  });

  it("rejects unknown vertex group with VERTEX_GROUP_NOT_FOUND", async () => {
    const res = await blenderPost("/vertex_group/delete", {
      objectName: "SkinMesh",
      vertexGroupName: "NoSuchGrp",
    });
    expect(res.ok).toBe(false);
    expect(res.errorCode).toBe("VERTEX_GROUP_NOT_FOUND");
  });

  it("adds and renames a shape key", async () => {
    const basis = await blenderPost("/shape_key/add", {
      objectName: "SkinMesh",
      name: "Basis_Custom",
    });
    expect(basis.ok).toBe(true);
    const add = await blenderPost<{ shapeKeyName: string }>("/shape_key/add", {
      objectName: "SkinMesh",
      name: "Smile",
    });
    expect(add.ok).toBe(true);
    expect(add.data?.shapeKeyName).toBe("Smile");

    const rename = await blenderPost<{ shapeKeyName: string }>("/shape_key/rename", {
      objectName: "SkinMesh",
      oldName: "Smile",
      newName: "BigSmile",
    });
    expect(rename.ok).toBe(true);
    expect(rename.data?.shapeKeyName).toBe("BigSmile");
  });

  it("rejects renaming missing shape key with SHAPE_KEY_NOT_FOUND", async () => {
    const res = await blenderPost("/shape_key/rename", {
      objectName: "SkinMesh",
      oldName: "DoesNotExist",
      newName: "Whatever",
    });
    expect(res.ok).toBe(false);
    expect(res.errorCode).toBe("SHAPE_KEY_NOT_FOUND");
  });

  it("adds a UE5 SOCKET_* empty under a parent object", async () => {
    const res = await blenderPost<{ socketObjectName: string }>("/socket/add", {
      objectName: "SocketParent",
      name: "Weapon_R",
      location: [0.2, 0, 0],
    });
    expect(res.ok).toBe(true);
    expect(res.data?.socketObjectName).toMatch(/^SOCKET_/);
  });

  it("keyframes a pose bone and adds an object constraint", async () => {
    await blenderPost("/action/create", { name: "PoseAction" });
    await blenderPost("/action/assign_to_object", {
      objectName: "Rig",
      actionName: "PoseAction",
    });
    const k = await blenderPost<{ insertedChannels: string[] }>("/keyframe/bone_pose", {
      armatureObjectName: "Rig",
      boneName: "Root",
      frame: 5,
    });
    expect(k.ok).toBe(true);
    expect(k.data?.insertedChannels.length).toBeGreaterThan(0);

    const c = await blenderPost<{ constraintName: string }>("/object/add_constraint", {
      objectName: "SocketParent",
      type: "COPY_LOCATION",
      targetObjectName: "Rig",
    });
    expect(c.ok).toBe(true);
    expect(c.data?.constraintName).toBeTruthy();
  });

  it("rejects unknown constraint type with INVALID_INPUT", async () => {
    const res = await blenderPost("/object/add_constraint", {
      objectName: "SocketParent",
      type: "NOT_A_REAL_CONSTRAINT_TYPE",
    });
    expect(res.ok).toBe(false);
    expect(res.errorCode).toBe("INVALID_INPUT");
  });
});
