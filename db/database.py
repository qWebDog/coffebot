    async def get_items(self, cat_id: int):
        rows = await (await self.conn.execute("SELECT id, category_id, name, photo_id, volumes_json FROM items WHERE category_id=?", (cat_id,))).fetchall()
        result = []
        for r in rows:
            vols_raw = json.loads(r[4]) if r[4] else {}
            # Преобразуем {vol_id: price} → {vol_id: {"name": ..., "price": ...}}
            vols_with_names = {}
            for vid, price in vols_raw.items():
                vol_name = next((v["name"] for v in await self.get_volumes() if v["id"] == int(vid)), "Std")
                vols_with_names[int(vid)] = {"name": vol_name, "price": float(price)}
            result.append({"id": r[0], "name": r[2], "volumes": vols_with_names})
        return result
