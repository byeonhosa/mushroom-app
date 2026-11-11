# Cultivation profiles for the varieties the farm's sources do not cover

For SRS SPR-2 and roadmap WP-3. The farm's own sources (Spore n Sprout; Michael Crowe / Southwest Mushrooms, in `backend/app/seeds/mushroom_species.json`) give profiles for eight species. The farm's list has eighteen varieties. The June dataset for the other ten was never committed and is not in the vault. This note records where the replacement values come from. About thirty minutes of searching, November 11, 2026.

**Every value below is marked `"data_source": "researched"` in `backend/app/seeds/species.json` and shown as researched on the species reference page.** They are starting points from suppliers and papers, not the farm's experience. Where a source gave no clean figure the value is left empty instead of guessed.

## How the eighteen are covered

| Varieties | Profile | Marked |
|---|---|---|
| Lion's Mane, Shiitake, Chestnut, Maitake, Reishi, Turkey Tail, King Trumpet | The farm's own profile for that species | farm |
| Blue, White, Pink and Golden Oyster | The farm's one "oyster" profile, shared by all four. Pink and golden like it warmer than blue and white; the shared fruiting range of 55 to 85 °F spans all four | farm (generic) |
| Black King Oyster | The King Trumpet profile. It is a hybrid of king trumpet and oyster and no separate source was found | researched |
| Pioppino, Nameko, Beech, Golden Enoki, White Enoki, Cordyceps | Below | researched |

## What the sources say

**Pioppino** (*Cyclocybe aegerita*, formerly *Agrocybe aegerita*). Incubation 21 to 27 °C for 3 to 4 weeks; primordia at 15 to 20 °C; fruiting 13 to 20 °C, ideal 15 °C; 85 to 95% humidity (higher at pinning); CO2 500 to 2,000 ppm; fresh air 4 to 8 exchanges an hour; 500 to 1,000 lux; fruiting takes 4 to 8 days; usually 2 flushes, sometimes 3, 10 to 14 days apart, the second unreliable. Biological efficiency is reported only as "below 100%", which is named as the obstacle to large-scale production; no figure is stored.
- https://lamycosphere.com/en/products/organic-piopino-cultivation-block
- https://northspore.com/products/pioppino-grain-spawn
- https://asianjournalofmycology.org/pdf/AJOM_5_1_3.pdf

**Nameko** (*Pholiota nameko*). Incubation 20 to 24 °C; colonization 2 to 4 weeks (one sheet says 16 to 19 days), then a resting period of 4 to 6 weeks; fruiting 7 to 18 °C, optimum 15 °C; humidity 95 to 100% at pinning and 85 to 95% after; CO2 500 to 1,000 ppm; 2 to 3 flushes. Substrate about 80% hardwood sawdust, 10% cereal, 10% bran. One source gives a much warmer fruiting range (18 to 28 °C) and one a much higher CO2 ceiling (5,000 ppm at pinning); the cooler, lower figures that most sources agree on are stored. No biological efficiency figure was found.
- https://northspore.com/products/nameko-mushroom-grain-spawn
- https://lamycosphere.com/en-de/products/mycelium-de-nameko-pholiota-nameko
- https://mycelia.be/?p=3690
- https://www.mushroommatter.com/details/item/602-cultivation-and-management-kernels-on-pholiota-nameko

**Enoki** (*Flammulina velutipes*), golden and white. One organism, two ways of growing it. Colonization about 25 days at 18 °C in the dark. **Golden**: fruiting at 10 to 18 °C (50 to 65 °F), humidity above 85%, CO2 kept low at 500 to 1,000 ppm, with light, which gives colour and open caps. **White**: the long white stems come from high CO2 and little light; a bottle study held 14 to 15 °C for the first ten days and then 7.5 to 9.5 °C, with humidity of 88 to 98%, and a 2025 study compared 1,000 with 10,000 ppm CO2 and found the high level keeps caps small. A fruiting cycle in bottles is about 28 days. No biological efficiency figure for either form was found.
- https://www.mdpi.com/2309-608X/11/8/551
- https://koreascience.kr/article/JAKO201909165769747.pdf
- https://northspore.com/products/organic-golden-enoki-mushroom-grow-kit-fruiting-block
- https://mycoboutique.com/blogs/instructions/growing-enoki-flammulina-velutipes-at-home

**Beech** (*Hypsizygus tessellatus*, sold as shimeji; the papers say *H. marmoreus*). The least complete. Pinning is induced at 13 to 15 °C and fruiting held at 15 to 18 °C; one study of a production house found its best result at 15.3 °C, 89.5% humidity, 870 lux and about 2,000 ppm CO2, with a biological conversion rate of 66%. High CO2 gives short thick stems. Mycelium was grown at 23 °C in one study. **No source gave the length of the spawn run or the days from pinning to harvest**; both are empty.
- https://doaj.org/article/c48bc4c877cc4a55bbd6d09ec6ef1c93
- https://eureka.patsnap.com/patent-CN101103676B

**Cordyceps** (*Cordyceps militaris*). Grown on grain (brown rice) in jars or tubs, not on the farm's sawdust blocks, so the bag workflow only loosely fits it. Fruiting 17 to 22 °C; humidity 70 to 95%; light is the trigger, 500 to 1,000 lux for 12 to 16 hours a day; 40 to 60 days from inoculation to harvest; 10 to 45 g fresh per container. Commercial strains degenerate over generations. Biological efficiency on a sawdust basis does not apply.
- https://koreascience.kr/article/JAKO200714364646051.pdf
- https://realmushrooms.com/blogs/rm/grow-cordyceps-mushrooms-indoors/
- https://gujaratdesertecology.com/wp-content/uploads/2023/08/SOP_Cordyceps-militaris-cultivation.pdf

## What was taken from this

- A profile row for every one of the eighteen, so that stage-overdue flags (DSH-4) and the forecast (RPT-8) have something to work from for each variety from the first day.
- A `data_source` on every profile and a note saying where it came from, shown on the reference page.
- Empty values where the sources were silent. The forecast must fall back to the farm's own averages or say it cannot forecast; it must not treat an empty value as zero.
- The first real runs of each researched variety should replace these figures (SPR-3, an administrator editing a profile, is not built yet).
