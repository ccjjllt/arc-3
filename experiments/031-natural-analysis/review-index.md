# 031 自然轨迹人工审阅索引

先看runs访问是否实际构造像素集合，再对齐原帧、stdout和后续行为。字段提及、函数定义、无异常返回都不足以单独证明采用。

| 游戏 | 臂 | 字段 | request日志行 | call ID | 工具返回 | 返回码0且无error |
|---|---|---|---:|---|---|---|
| ft09-0d8bbf25 | segmentation_runs | runs | 3 | call_ae4136e32f834cb180b338e3 | True | True |
| cd82-fb555c5d | segmentation_runs | runs | 3 | call_5675cb224b6e447bbd19d703 | True | True |
| cd82-fb555c5d | segmentation_runs | runs | 13 | call_eccbc3d86f1a42f8b24000ad | True | True |
| cd82-fb555c5d | segmentation_runs | runs | 25 | call_22deffb553b94a759ea2a415 | True | True |
| cd82-fb555c5d | segmentation_runs | runs | 27 | call_01b555b47ca04a2bb96b41bf | True | True |
| cd82-fb555c5d | segmentation_runs | runs | 33 | call_56dd0c21122e42f3880c39c7 | True | True |
| cd82-fb555c5d | segmentation_runs | runs | 37 | call_e000d776991d48dcaab4f408 | True | True |
| cd82-fb555c5d | segmentation_runs | runs | 39 | call_57754c4f60a8491ab90a8068 | True | True |
| cd82-fb555c5d | segmentation_runs | runs | 41 | call_6174e11a2b364bc1b008d447 | True | True |
| cd82-fb555c5d | segmentation_runs | runs | 43 | call_073d5300880e4c5b87d11fdb | True | True |
| cd82-fb555c5d | segmentation_runs | runs | 47 | call_e2e34b1656384ef5bc3b1b74 | True | True |
| re86-8af5384d | segmentation_runs | boundary,runs | 3 | call_e26ab63ee7834500b76e9caf | True | True |
| re86-8af5384d | segmentation_runs | runs | 5 | call_244a7913b57e4449b9486906 | True | True |
| re86-8af5384d | segmentation_runs | runs | 9 | call_5f9f19354934464d80772132 | True | True |
| re86-8af5384d | segmentation_runs | runs | 11 | call_d71cf8c4ab7c4ba4a02aceff | True | True |
| re86-8af5384d | segmentation_runs | runs | 15 | call_e05fb5af5feb44738cd155f2 | True | True |
| re86-8af5384d | segmentation_runs | runs | 21 | call_015450d3f72e4f248e80c54d | True | True |
| re86-8af5384d | segmentation_runs | runs | 23 | call_c6d8aa36335449f3b32d7d1b | True | True |
| re86-8af5384d | segmentation_runs | runs | 25 | call_84e9c6d69a4b45b699f9dac7 | True | True |
| re86-8af5384d | segmentation_runs | runs | 27 | call_0a06c4901ca64e5688ab77c7 | True | True |
| re86-8af5384d | segmentation_runs | runs | 29 | call_956c60ccb1eb43f6a91040ae | True | True |
| re86-8af5384d | segmentation_runs | runs | 31 | call_cbfc26ccc9a24c8faaee6918 | True | True |
| re86-8af5384d | segmentation_runs | runs | 33 | call_4d01e2ec819d4fb88712985a | True | True |
| re86-8af5384d | segmentation_runs | runs | 35 | call_58a9013cc90a40d0aa5ac45d | True | True |
| re86-8af5384d | segmentation_runs | runs | 37 | call_834725449ffe46adac596273 | True | True |
| re86-8af5384d | segmentation_runs | runs | 39 | call_3526f7e86b9f4338bedd3a00 | True | True |
| re86-8af5384d | segmentation_runs | runs | 47 | call_8839b05e81e84f42b376197e | True | True |
| re86-8af5384d | segmentation_runs | runs | 49 | call_d0001258ef454e99aa38ec01 | True | True |
| re86-8af5384d | segmentation_runs | runs | 51 | call_adbcb756ade842f2879b46e1 | True | False |
| re86-8af5384d | segmentation_runs | runs | 53 | call_181a6daece1e4800bda681ea | True | True |
| re86-8af5384d | segmentation_runs | runs | 55 | call_78e9f94a6e954359a7cf5a3a | True | True |
| re86-8af5384d | segmentation_runs | runs | 59 | call_5b92f27d82b14717be7d81bc | True | True |
| re86-8af5384d | segmentation_runs | runs | 63 | call_9d7a46aad1fc446e9c0fd3ea | True | True |
| re86-8af5384d | segmentation_runs | runs | 65 | call_dd16a4cfe4794c16a7013b9f | True | True |
| re86-8af5384d | segmentation_runs | runs | 67 | call_bdf0b36d15c84ba2af6d40ef | True | True |
| r11l-495a7899 | segmentation_runs | runs | 3 | call_6dd36afa3a8d42849e884671 | True | True |
| r11l-495a7899 | segmentation_runs | runs | 9 | call_eacb6256c5234416b7a47e80 | True | True |
| r11l-495a7899 | segmentation_runs | runs | 21 | call_ea2e87fc86fe46489b764b61 | True | True |
| r11l-495a7899 | segmentation_runs | runs | 27 | call_77ba881468614ce581391be9 | True | True |
| r11l-495a7899 | segmentation_runs | runs | 37 | call_6434be55cd824f34adc9cda4 | True | False |
| r11l-495a7899 | segmentation_runs | runs | 39 | call_a59813a6e9f145bf81f4bb27 | True | True |
| r11l-495a7899 | segmentation_runs | runs | 55 | call_62e30c891c0a492e94c2507b | True | True |
| r11l-495a7899 | segmentation_runs | runs | 57 | call_aa4bcd60e4914041921fbb6a | True | False |
| r11l-495a7899 | segmentation_runs | runs | 59 | call_bdbbba6fd7b14c91b2f2a691 | True | True |
| r11l-495a7899 | segmentation_runs | runs | 65 | call_da7b7b70b22842ce84d8e910 | True | True |
| sp80-589a99af | segmentation_runs | runs | 3 | call_92a0b27923aa4b44ba596d6a | True | True |
| sp80-589a99af | segmentation_runs | runs | 7 | call_e30416cc2c8a49b8be440ba8 | True | True |
| sp80-589a99af | segmentation_runs | runs | 15 | call_043da88967404b98ad079d6c | True | True |
| sp80-589a99af | segmentation_runs | runs | 17 | call_9d697ecd6b69467182eb1066 | True | True |
| sp80-589a99af | segmentation_runs | runs | 19 | call_ad1dde9f4a03499baa4a03ad | True | True |
| sp80-589a99af | segmentation_runs | runs | 21 | call_aa54c3300cc34469a4d1fc8c | True | True |
| sp80-589a99af | segmentation_runs | runs | 23 | call_5a3685c533cc4a66b0d79c1c | True | True |
| sp80-589a99af | segmentation_runs | runs | 25 | call_c8edd2e038ba4bccb61dafc7 | True | True |
| sp80-589a99af | segmentation_runs | runs | 27 | call_30d1ad936a2746248e71e920 | True | True |
| sp80-589a99af | segmentation_runs | runs | 31 | call_f02829bf753543aea11c6932 | True | True |
| sp80-589a99af | segmentation_runs | runs | 33 | call_354ccebfae3a41fc84d25069 | True | True |
| sp80-589a99af | segmentation_runs | runs | 35 | call_e5069c0b77884914b2a0d6e8 | True | True |
| sp80-589a99af | segmentation_runs | runs | 37 | call_9b5961592570455ebae5c6bb | True | True |
| tu93-0768757b | segmentation_runs | runs | 3 | call_1ee0a2ff77744772a9b5ba8e | True | True |
| tu93-0768757b | segmentation_runs | runs | 17 | call_c2c9371c9e904642b03e415b | True | True |
| tu93-0768757b | segmentation_runs | runs | 27 | call_12b56025a71d4192b6032337 | True | True |
| tu93-0768757b | segmentation_runs | runs | 29 | call_a930711b83644f0cae23a9b6 | True | False |
| tu93-0768757b | segmentation_runs | runs | 43 | call_2d993bae242d4602acb4b342 | True | True |
| tu93-0768757b | segmentation_runs | runs | 45 | call_8583106ffd424c3eb0f31b4c | True | True |
| tu93-0768757b | segmentation_runs | runs | 49 | call_46a81c107343419bb520bfce | True | True |
| tu93-0768757b | segmentation_runs | runs | 51 | call_5952161cfec6479eb01e710d | True | True |
| tu93-0768757b | segmentation_runs | runs | 55 | call_5f29a8c125e94dcba566859a | True | True |
| tu93-0768757b | segmentation_runs | runs | 57 | call_89c89b1016654729a71af1dd | True | True |
| tu93-0768757b | segmentation_runs | runs | 61 | call_bd2bdae70193401a8da013ff | True | True |
| sc25-635fd71a | segmentation_runs | boundary,runs | 3 | call_affc092fddea43068509f0f9 | True | True |
| sc25-635fd71a | segmentation_runs | runs | 11 | call_9134be6b60564b39bc3beff1 | True | True |
| sc25-635fd71a | segmentation_runs | runs | 13 | call_79ed8fe0104448988421593c | True | True |
| sc25-635fd71a | segmentation_runs | runs | 15 | call_1340115ae9214a1292a1ff14 | True | False |
| sc25-635fd71a | segmentation_runs | runs | 17 | call_9d20aeef85044f64bdbb6770 | True | True |
| sc25-635fd71a | segmentation_runs | runs | 23 | call_f9f46cb533f448c283aefee3 | True | True |
| sc25-635fd71a | segmentation_runs | runs | 25 | call_f3d52039a2ca432ba804ab81 | True | True |
| sc25-635fd71a | segmentation_runs | runs | 31 | call_4bcefd1156ab41b0aeb0b30c | True | True |
| sc25-635fd71a | segmentation_runs | runs | 37 | call_a63b25e8dcc744a0ac2ceb3d | True | True |
| sc25-635fd71a | segmentation_runs | runs | 45 | call_e0971e4bac8843aea6f91a4c | True | True |
| sc25-635fd71a | segmentation_runs | runs | 49 | call_baf0ce47b5ad45e2920e55b5 | True | True |
| sc25-635fd71a | segmentation_runs | runs | 51 | call_1de02e2c011144059d627c5c | True | True |
| sc25-635fd71a | segmentation_runs | runs | 55 | call_e82f3891d25d4f2e99205b8a | True | True |
| sc25-635fd71a | segmentation_runs | runs | 57 | call_d5759fb9b08343afaf5712eb | True | True |
| sc25-635fd71a | segmentation_runs | runs | 59 | call_0476152392e1474dade1af03 | True | True |
| sc25-635fd71a | segmentation_runs | runs | 61 | call_3d901d8bff40454b8869ed0f | True | True |
| sc25-635fd71a | segmentation_runs | runs | 73 | call_96ef624c36474a0cb5fb790f | True | True |
| sc25-635fd71a | segmentation_runs | runs | 79 | call_5fd87971579e4ee484062c54 | True | True |
| sc25-635fd71a | segmentation_runs | runs | 83 | call_ee7a96eb53834a1c82d51c90 | True | True |
| sc25-635fd71a | segmentation_runs | runs | 85 | call_25a8e82d5d674afdb890b704 | True | True |
| ar25-0c556536 | segmentation_runs | runs | 3 | call_63c2c4259a8446ebb93f8672 | True | True |
| ar25-0c556536 | segmentation_runs | runs | 7 | call_8e3398d194f44c75a16dcd43 | True | True |
| ar25-0c556536 | segmentation_runs | runs | 11 | call_f3304bd78380476db7d5aca1 | True | True |
| ar25-0c556536 | segmentation_runs | runs | 13 | call_e716c8b5d4e6428583faa5cf | True | True |
| ar25-0c556536 | segmentation_runs | runs | 15 | call_af3888029cd943408c6c72bc | True | True |
| ar25-0c556536 | segmentation_runs | runs | 17 | call_fecc96f3190349baa5030606 | True | True |
| ar25-0c556536 | segmentation_runs | runs | 19 | call_ffb4025fe5c541408d79e305 | True | True |
| ar25-0c556536 | segmentation_runs | runs | 21 | call_6451f0deae6047d69e974697 | True | True |
| ar25-0c556536 | segmentation_runs | runs | 23 | call_1138f7ef820149b99aea2191 | True | False |
| ar25-0c556536 | segmentation_runs | runs | 25 | call_6b6e9ec59e0d4cb29a4fd429 | True | True |
| ar25-0c556536 | segmentation_runs | runs | 39 | call_d69958803faf45c1ac5188df | True | True |
| ar25-0c556536 | segmentation_runs | runs | 43 | call_6b77543c10dd4c4d9d502668 | True | True |
| ar25-0c556536 | segmentation_runs | runs | 45 | call_9ccea8f41c0e43e9bdc8723d | True | True |
| ar25-0c556536 | segmentation_runs | runs | 55 | call_b98322a27c9d40d18031ca4a | True | True |
| ar25-0c556536 | segmentation_runs | runs | 59 | call_c83f7645cb784f299001fb3d | True | True |
| ar25-0c556536 | segmentation_runs | runs | 61 | call_14fba814a88a43ef9204e1e7 | True | True |
| ar25-0c556536 | segmentation_runs | runs | 63 | call_10428c285a244b01921cd91a | True | True |
| ar25-0c556536 | segmentation_runs | runs | 65 | call_f72d3e39f2ac4502b1fe9da3 | True | True |
| ar25-0c556536 | segmentation_runs | runs | 67 | call_1725ea8e350f4c6c85e6d20c | True | True |
| ar25-0c556536 | segmentation_runs | runs | 73 | call_e4fcdbd17ec04421812e1c3d | True | True |
| ar25-0c556536 | segmentation_runs | runs | 75 | call_828ff89e07e24ee29749ff39 | True | True |
| ar25-0c556536 | segmentation_runs | runs | 77 | call_ce5acabbccc9431cadf61e4d | True | True |
| ar25-0c556536 | segmentation_runs | runs | 81 | call_b91cf51cea2c4a5a8b6aa866 | True | True |
| ar25-0c556536 | segmentation_runs | runs | 85 | call_a674c00e7a654bfbb1bae9b1 | True | True |
| ar25-0c556536 | segmentation_runs | runs | 89 | call_62ffd011b2fb47879b111541 | True | True |
| ar25-0c556536 | segmentation_runs | runs | 91 | call_82a55d9da3bf4b4b9ff50846 | True | True |
| m0r0-492f87ba | segmentation_runs | runs | 3 | call_c444cb85b20e4cc5b2bd3d74 | True | True |
| m0r0-492f87ba | segmentation_runs | runs | 5 | call_1d571657b6664ebc822c9de8 | True | True |
| m0r0-492f87ba | segmentation_runs | runs | 9 | call_d89e7aa00231492b9bff762e | True | True |
| m0r0-492f87ba | segmentation_runs | runs | 33 | call_2f929a5b4c2345319d6a3778 | True | True |
| m0r0-492f87ba | segmentation_runs | runs | 47 | call_0cd0f354a1424ae0a19859af | True | True |
| tr87-cd924810 | segmentation_runs | boundary,runs | 3 | call_422cc90409c24d35a88f4530 | True | True |
| tr87-cd924810 | segmentation_runs | runs | 9 | call_796d278b4cd74b1183a77c7e | True | True |
| tr87-cd924810 | segmentation_runs | runs | 15 | call_051fd58e251241cfb9b4648d | True | True |
| tr87-cd924810 | segmentation_runs | runs | 29 | call_74ca916e411747e4b43ca426 | True | True |
| tr87-cd924810 | segmentation_runs | runs | 31 | call_334fe460ab3a411fa1f65fc6 | True | True |
| tr87-cd924810 | segmentation_runs | runs | 33 | call_05be22be63884943aa5e344d | True | True |
| tr87-cd924810 | segmentation_runs | runs | 35 | call_38cd986a49924b3cb135da80 | True | True |
| tr87-cd924810 | segmentation_runs | runs | 53 | call_117c7702d9054881b8451eb1 | True | True |
| tr87-cd924810 | segmentation_runs | runs | 59 | call_f13d7b03e347435f8a8fce76 | True | True |
| tr87-cd924810 | segmentation_runs | runs | 69 | call_c6fa542ef7a14196a7703c20 | True | True |
| tr87-cd924810 | segmentation_runs | runs | 89 | call_dada33329039431ab859428a | True | True |
| ft09-0d8bbf25 | baseline | boundary | 3 | call_7c5d1d665ba247e78c1ff282 | True | True |
| ft09-0d8bbf25 | baseline | boundary | 11 | call_756bad72bad34e64a036ee2d | True | False |
| cd82-fb555c5d | baseline | boundary | 3 | call_1aaff7811fd241c4b8858ffe | True | True |
| cd82-fb555c5d | baseline | boundary | 7 | call_fcaa000a1112496ea3895f22 | True | False |
| cd82-fb555c5d | baseline | boundary | 9 | call_b57d7b9223e24e3a866142f1 | True | True |
| cd82-fb555c5d | baseline | boundary | 27 | call_0fbc1b1f9fc14cf6bd7db5fa | True | True |
| cd82-fb555c5d | baseline | boundary | 33 | call_004551ec7943417b8ad69468 | True | True |
| cd82-fb555c5d | baseline | boundary | 49 | call_f51268db453d45d2988a7dad | True | True |
| cd82-fb555c5d | baseline | boundary | 57 | call_4a4758d6f9ee4fdaa7ee2ad9 | True | True |
| cd82-fb555c5d | baseline | boundary | 63 | call_2608b16bb4324cab997d4836 | True | True |
| cd82-fb555c5d | baseline | boundary | 65 | call_78ab833a8a794c2ca626d628 | True | True |
| cd82-fb555c5d | baseline | boundary | 69 | call_0d1573e29c9f4100bb09a20d | True | True |
| re86-8af5384d | baseline | boundary | 3 | call_7e4ee08bf269479c8395b28f | True | True |
| re86-8af5384d | baseline | boundary | 21 | call_4ce52fafd37142dcb2e405c4 | True | True |
| re86-8af5384d | baseline | boundary | 35 | call_45e388a8584541e78adafa49 | True | True |
| re86-8af5384d | baseline | boundary | 53 | call_356e841a58194c8f9c709b8a | True | True |
| re86-8af5384d | baseline | boundary | 79 | call_a19ea62a15784748a1a4d692 | True | True |
| r11l-495a7899 | baseline | boundary | 3 | call_b1605124db3243fc82acbf49 | True | True |
| r11l-495a7899 | baseline | boundary | 7 | call_c787e1d119454d0cb2436d08 | True | True |
| r11l-495a7899 | baseline | boundary | 13 | call_ebc5954a095e4f0f8160619e | True | True |
| r11l-495a7899 | baseline | boundary | 17 | call_0810af7240c84695a77b61f6 | True | False |
| r11l-495a7899 | baseline | boundary | 19 | call_85614ae532eb46c3bbbe3177 | True | True |
| r11l-495a7899 | baseline | boundary | 21 | call_9a57626277a24e1c976aef9c | True | True |
| r11l-495a7899 | baseline | boundary | 23 | call_05bf1bbebc2543c88e7fec6f | True | True |
| r11l-495a7899 | baseline | boundary | 25 | call_c75511427428437a894f68ba | True | True |
| r11l-495a7899 | baseline | boundary | 33 | call_a58a4e7faed04399abafa020 | True | True |
| r11l-495a7899 | baseline | boundary | 41 | call_168c58058f8e457b8b9f2611 | True | True |
| r11l-495a7899 | baseline | boundary | 49 | call_a2064a4f3d8843ba8d115028 | True | True |
| r11l-495a7899 | baseline | boundary | 51 | call_7d6e6b6d69cf48eeb67039a3 | True | True |
| sp80-589a99af | baseline | boundary | 3 | call_67865606e8984b1d8b796c88 | True | True |
| sp80-589a99af | baseline | boundary | 15 | call_b88e3a34acce4e60ad0040a0 | True | True |
| sp80-589a99af | baseline | boundary | 21 | call_d159ca5c5f26488b83526be1 | True | True |
| sp80-589a99af | baseline | boundary | 23 | call_3c83179c97fe496eababcd35 | True | True |
| sp80-589a99af | baseline | boundary | 27 | call_b9757cdd648c46e48470dede | True | True |
| sp80-589a99af | baseline | boundary | 29 | call_6bb8307919d64a63b98ec81b | True | True |
| sp80-589a99af | baseline | boundary | 33 | call_2043f94acac5467b8cbe66d3 | True | True |
| sp80-589a99af | baseline | boundary | 35 | call_fdc3720d3c4642d0aff4c31e | True | True |
| sp80-589a99af | baseline | boundary | 39 | call_b234d2c82cce45938cd2539f | True | False |
| sp80-589a99af | baseline | boundary | 43 | call_331cd36ecfc74ec78f5079a0 | True | True |
| sp80-589a99af | baseline | boundary | 49 | call_990ca4574d0845a3b0a3988b | True | False |
| sp80-589a99af | baseline | boundary | 51 | call_6781bcce674b42178caf0d34 | True | True |
| tu93-0768757b | baseline | boundary | 3 | call_f2b8b92c5a824d68aae6fed6 | True | True |
| tu93-0768757b | baseline | boundary | 5 | call_b6e4d9b60e0245268296e3a1 | True | True |
| tu93-0768757b | baseline | boundary | 7 | call_d7712b4be82949c188d4c50a | True | True |
| tu93-0768757b | baseline | boundary | 11 | call_bdebe0e2cf624ffaa017eff8 | True | True |
| tu93-0768757b | baseline | boundary | 25 | call_20b9bf5d52d243ca9d8e8a01 | True | True |
| sc25-635fd71a | baseline | boundary | 3 | call_bd6f4d6703ec4d5ebbdf202d | True | True |
| sc25-635fd71a | baseline | boundary | 27 | call_ab367dbcfd9148be898e4528 | True | True |
| sc25-635fd71a | baseline | boundary | 55 | call_78ab8084dc67493ca318b73a | True | True |
| sc25-635fd71a | baseline | boundary | 63 | call_54ad1c565cb74c9ba06d607f | True | True |
| sc25-635fd71a | baseline | boundary | 89 | call_7f33d7a0aa1e4f14be3d65b8 | True | True |
| ar25-0c556536 | baseline | boundary | 3 | call_2f3ecaf0c38746b4932a44c2 | True | True |
| ar25-0c556536 | baseline | boundary | 11 | call_1e015717834f491ca0c2fdd1 | True | True |
| ar25-0c556536 | baseline | boundary | 13 | call_87a712b92b574380b120451b | True | True |
| ar25-0c556536 | baseline | boundary | 15 | call_f21dc5eb68e34ec5aed7b03d | True | True |
| ar25-0c556536 | baseline | boundary | 19 | call_06414356d12e420c88968a3e | True | True |
| ar25-0c556536 | baseline | boundary | 21 | call_ead63f66f7674da6a0a0c2fd | True | True |
| ar25-0c556536 | baseline | boundary | 29 | call_2eeb3170c9884460b529cbb9 | True | True |
| ar25-0c556536 | baseline | boundary | 33 | call_fa272e4c553b441c9e77fd9d | True | True |
| ar25-0c556536 | baseline | boundary | 35 | call_1d21c8fc5aff4d5db27822ba | True | True |
| ar25-0c556536 | baseline | boundary | 41 | call_d674d365e5c743ea8b5c1ce1 | True | True |
| ar25-0c556536 | baseline | boundary | 43 | call_e77957ae0d70432aa8c4d992 | True | True |
| ar25-0c556536 | baseline | boundary | 45 | call_7c07ad38a0644ce8b335dc54 | True | True |
| ar25-0c556536 | baseline | boundary | 47 | call_5427a164833045d7bd9642f1 | True | True |
| ar25-0c556536 | baseline | boundary | 49 | call_cda26376fea34e23b3f744cd | True | True |
| ar25-0c556536 | baseline | boundary | 51 | call_20a51d62100d4998a60ea5af | True | True |
| ar25-0c556536 | baseline | boundary | 53 | call_c3aeb39f381148c48756764c | True | True |
| ar25-0c556536 | baseline | boundary | 57 | call_6f1ce1f434764dd8b2830c3c | True | True |
| ar25-0c556536 | baseline | boundary | 59 | call_f01dad635f694202a0ccb731 | True | True |
| ar25-0c556536 | baseline | boundary | 73 | call_b6084f3408ed400485bc1f95 | True | True |
| m0r0-492f87ba | baseline | boundary | 3 | call_f3c0ff6993ae424596ccb7c9 | True | True |
| m0r0-492f87ba | baseline | boundary | 27 | call_426afd24e9104b3ea46674fc | True | True |
| m0r0-492f87ba | baseline | boundary | 31 | call_54c18cc1ccc9477aa9a78863 | True | True |
| m0r0-492f87ba | baseline | boundary | 33 | call_c8c20c1039024af9b92e8f77 | True | True |
| m0r0-492f87ba | baseline | boundary | 37 | call_178737b774974edcbab4d490 | True | True |
| m0r0-492f87ba | baseline | boundary | 39 | call_642023218662462e9ed600bb | True | True |
| m0r0-492f87ba | baseline | boundary | 41 | call_db57bcf2dd7f47ceacc1bd85 | True | True |
| m0r0-492f87ba | baseline | boundary | 59 | call_b6c533e8a516455e85a0c2c3 | True | True |
| tr87-cd924810 | baseline | boundary | 3 | call_f31490aa3a434bcb966b2b69 | True | True |
| tr87-cd924810 | baseline | boundary | 11 | call_9644e62a92754081955ef848 | True | True |
| tr87-cd924810 | baseline | boundary | 13 | call_bd646cd87eba4c13a596bb17 | True | True |
| tr87-cd924810 | baseline | boundary | 25 | call_abb5d316edd2491f9ad0863a | True | True |
| tr87-cd924810 | baseline | boundary | 27 | call_f85da2ebc029449eb9a7c3c8 | True | False |
| tr87-cd924810 | baseline | boundary | 37 | call_4e24258c984441478a2e6140 | True | True |
| tr87-cd924810 | baseline | boundary | 51 | call_4669a6667c714fd5a815a8bb | True | True |
| tr87-cd924810 | baseline | boundary | 73 | call_e9d12eec92714fabb6a6bcbd | True | True |
| tr87-cd924810 | baseline | boundary | 85 | call_c146c0d685214b64ad97107e | True | True |

## ft09-0d8bbf25 · segmentation_runs · call_ae4136e32f834cb180b338e3

原件：runs/031-natural-aligned/segmentation_runs/ft09-0d8bbf25_p0_requests.jsonl:3；analysis_step=1，snapshot_action=2。

```json
[
  {
    "field": "runs",
    "kind": "subscript_load",
    "code_line": 7,
    "expression": "n['runs']",
    "enclosing_scopes": [
      "For"
    ]
  }
]
```

## cd82-fb555c5d · segmentation_runs · call_5675cb224b6e447bbd19d703

原件：runs/031-natural-aligned/segmentation_runs/cd82-fb555c5d_p0_requests.jsonl:3；analysis_step=1，snapshot_action=1。

```json
[
  {
    "field": "runs",
    "kind": "subscript_load",
    "code_line": 5,
    "expression": "n['runs']",
    "enclosing_scopes": [
      "For"
    ]
  }
]
```

## cd82-fb555c5d · segmentation_runs · call_eccbc3d86f1a42f8b24000ad

原件：runs/031-natural-aligned/segmentation_runs/cd82-fb555c5d_p0_requests.jsonl:13；analysis_step=5，snapshot_action=5。

```json
[
  {
    "field": "runs",
    "kind": "subscript_load",
    "code_line": 3,
    "expression": "n['runs']",
    "enclosing_scopes": [
      "For"
    ]
  },
  {
    "field": "runs",
    "kind": "subscript_load",
    "code_line": 3,
    "expression": "n['runs']",
    "enclosing_scopes": [
      "For"
    ]
  }
]
```

## cd82-fb555c5d · segmentation_runs · call_22deffb553b94a759ea2a415

原件：runs/031-natural-aligned/segmentation_runs/cd82-fb555c5d_p0_requests.jsonl:25；analysis_step=9，snapshot_action=13。

```json
[
  {
    "field": "runs",
    "kind": "subscript_load",
    "code_line": 9,
    "expression": "n['runs']",
    "enclosing_scopes": [
      "For",
      "FunctionDef"
    ]
  },
  {
    "field": "runs",
    "kind": "subscript_load",
    "code_line": 9,
    "expression": "n['runs']",
    "enclosing_scopes": [
      "For",
      "FunctionDef"
    ]
  }
]
```

## cd82-fb555c5d · segmentation_runs · call_01b555b47ca04a2bb96b41bf

原件：runs/031-natural-aligned/segmentation_runs/cd82-fb555c5d_p0_requests.jsonl:27；analysis_step=10，snapshot_action=15。

```json
[
  {
    "field": "runs",
    "kind": "subscript_load",
    "code_line": 6,
    "expression": "n['runs']",
    "enclosing_scopes": [
      "For"
    ]
  },
  {
    "field": "runs",
    "kind": "subscript_load",
    "code_line": 6,
    "expression": "n['runs']",
    "enclosing_scopes": [
      "For"
    ]
  },
  {
    "field": "runs",
    "kind": "subscript_load",
    "code_line": 7,
    "expression": "n['runs']",
    "enclosing_scopes": [
      "If",
      "For"
    ]
  },
  {
    "field": "runs",
    "kind": "subscript_load",
    "code_line": 7,
    "expression": "n['runs']",
    "enclosing_scopes": [
      "If",
      "For"
    ]
  }
]
```

## cd82-fb555c5d · segmentation_runs · call_56dd0c21122e42f3880c39c7

原件：runs/031-natural-aligned/segmentation_runs/cd82-fb555c5d_p0_requests.jsonl:33；analysis_step=12，snapshot_action=21。

```json
[
  {
    "field": "runs",
    "kind": "subscript_load",
    "code_line": 5,
    "expression": "n['runs']",
    "enclosing_scopes": [
      "For"
    ]
  },
  {
    "field": "runs",
    "kind": "subscript_load",
    "code_line": 13,
    "expression": "n['runs']",
    "enclosing_scopes": [
      "For"
    ]
  }
]
```

## cd82-fb555c5d · segmentation_runs · call_e000d776991d48dcaab4f408

原件：runs/031-natural-aligned/segmentation_runs/cd82-fb555c5d_p0_requests.jsonl:37；analysis_step=13，snapshot_action=24。

```json
[
  {
    "field": "runs",
    "kind": "subscript_load",
    "code_line": 6,
    "expression": "n['runs']",
    "enclosing_scopes": [
      "If",
      "For",
      "FunctionDef"
    ]
  },
  {
    "field": "runs",
    "kind": "subscript_load",
    "code_line": 5,
    "expression": "n['runs']",
    "enclosing_scopes": [
      "If",
      "For",
      "FunctionDef"
    ]
  }
]
```

## cd82-fb555c5d · segmentation_runs · call_57754c4f60a8491ab90a8068

原件：runs/031-natural-aligned/segmentation_runs/cd82-fb555c5d_p0_requests.jsonl:39；analysis_step=14，snapshot_action=26。

```json
[
  {
    "field": "runs",
    "kind": "subscript_load",
    "code_line": 7,
    "expression": "n['runs']",
    "enclosing_scopes": []
  },
  {
    "field": "runs",
    "kind": "subscript_load",
    "code_line": 7,
    "expression": "n['runs']",
    "enclosing_scopes": []
  },
  {
    "field": "runs",
    "kind": "subscript_load",
    "code_line": 7,
    "expression": "n['runs']",
    "enclosing_scopes": [
      "comprehension"
    ]
  }
]
```

## cd82-fb555c5d · segmentation_runs · call_6174e11a2b364bc1b008d447

原件：runs/031-natural-aligned/segmentation_runs/cd82-fb555c5d_p0_requests.jsonl:41；analysis_step=15，snapshot_action=30。

```json
[
  {
    "field": "runs",
    "kind": "subscript_load",
    "code_line": 4,
    "expression": "n['runs']",
    "enclosing_scopes": [
      "FunctionDef"
    ]
  },
  {
    "field": "runs",
    "kind": "subscript_load",
    "code_line": 3,
    "expression": "n['runs']",
    "enclosing_scopes": [
      "FunctionDef"
    ]
  },
  {
    "field": "runs",
    "kind": "subscript_load",
    "code_line": 3,
    "expression": "n['runs']",
    "enclosing_scopes": [
      "FunctionDef"
    ]
  },
  {
    "field": "runs",
    "kind": "subscript_load",
    "code_line": 3,
    "expression": "n['runs']",
    "enclosing_scopes": [
      "comprehension",
      "FunctionDef"
    ]
  },
  {
    "field": "runs",
    "kind": "subscript_load",
    "code_line": 4,
    "expression": "n['runs']",
    "enclosing_scopes": [
      "comprehension",
      "FunctionDef"
    ]
  }
]
```

## cd82-fb555c5d · segmentation_runs · call_073d5300880e4c5b87d11fdb

原件：runs/031-natural-aligned/segmentation_runs/cd82-fb555c5d_p0_requests.jsonl:43；analysis_step=16，snapshot_action=32。

```json
[
  {
    "field": "runs",
    "kind": "subscript_load",
    "code_line": 5,
    "expression": "n['runs']",
    "enclosing_scopes": [
      "For"
    ]
  }
]
```

## cd82-fb555c5d · segmentation_runs · call_e2e34b1656384ef5bc3b1b74

原件：runs/031-natural-aligned/segmentation_runs/cd82-fb555c5d_p0_requests.jsonl:47；analysis_step=18，snapshot_action=38。

```json
[
  {
    "field": "runs",
    "kind": "subscript_load",
    "code_line": 5,
    "expression": "n['runs']",
    "enclosing_scopes": [
      "For"
    ]
  }
]
```

## re86-8af5384d · segmentation_runs · call_e26ab63ee7834500b76e9caf

原件：runs/031-natural-aligned/segmentation_runs/re86-8af5384d_p0_requests.jsonl:3；analysis_step=1，snapshot_action=1。

```json
[
  {
    "field": "runs",
    "kind": "subscript_load",
    "code_line": 7,
    "expression": "n['runs']",
    "enclosing_scopes": [
      "For"
    ]
  },
  {
    "field": "boundary",
    "kind": "subscript_load",
    "code_line": 7,
    "expression": "n['boundary']",
    "enclosing_scopes": [
      "For"
    ]
  }
]
```

## re86-8af5384d · segmentation_runs · call_244a7913b57e4449b9486906

原件：runs/031-natural-aligned/segmentation_runs/re86-8af5384d_p0_requests.jsonl:5；analysis_step=1，snapshot_action=1。

```json
[
  {
    "field": "runs",
    "kind": "subscript_load",
    "code_line": 6,
    "expression": "y['runs']",
    "enclosing_scopes": []
  },
  {
    "field": "runs",
    "kind": "subscript_load",
    "code_line": 5,
    "expression": "y['runs']",
    "enclosing_scopes": [
      "comprehension",
      "comprehension",
      "comprehension"
    ]
  }
]
```

## re86-8af5384d · segmentation_runs · call_5f9f19354934464d80772132

原件：runs/031-natural-aligned/segmentation_runs/re86-8af5384d_p0_requests.jsonl:9；analysis_step=3，snapshot_action=3。

```json
[
  {
    "field": "runs",
    "kind": "subscript_load",
    "code_line": 5,
    "expression": "n['runs']",
    "enclosing_scopes": [
      "If",
      "For"
    ]
  }
]
```

## re86-8af5384d · segmentation_runs · call_d71cf8c4ab7c4ba4a02aceff

原件：runs/031-natural-aligned/segmentation_runs/re86-8af5384d_p0_requests.jsonl:11；analysis_step=4，snapshot_action=6。

```json
[
  {
    "field": "runs",
    "kind": "subscript_load",
    "code_line": 5,
    "expression": "n['runs']",
    "enclosing_scopes": [
      "If",
      "For",
      "FunctionDef"
    ]
  },
  {
    "field": "runs",
    "kind": "subscript_load",
    "code_line": 11,
    "expression": "n['runs']",
    "enclosing_scopes": [
      "FunctionDef"
    ]
  },
  {
    "field": "runs",
    "kind": "subscript_load",
    "code_line": 11,
    "expression": "n['runs']",
    "enclosing_scopes": [
      "FunctionDef"
    ]
  }
]
```

## re86-8af5384d · segmentation_runs · call_e05fb5af5feb44738cd155f2

原件：runs/031-natural-aligned/segmentation_runs/re86-8af5384d_p0_requests.jsonl:15；analysis_step=5，snapshot_action=13。

```json
[
  {
    "field": "runs",
    "kind": "subscript_load",
    "code_line": 3,
    "expression": "n['runs']",
    "enclosing_scopes": [
      "FunctionDef"
    ]
  },
  {
    "field": "runs",
    "kind": "subscript_load",
    "code_line": 8,
    "expression": "n['runs']",
    "enclosing_scopes": [
      "For",
      "FunctionDef"
    ]
  },
  {
    "field": "runs",
    "kind": "subscript_load",
    "code_line": 8,
    "expression": "n['runs']",
    "enclosing_scopes": [
      "For",
      "FunctionDef"
    ]
  },
  {
    "field": "runs",
    "kind": "subscript_load",
    "code_line": 9,
    "expression": "n['runs']",
    "enclosing_scopes": [
      "FunctionDef"
    ]
  }
]
```

## re86-8af5384d · segmentation_runs · call_015450d3f72e4f248e80c54d

原件：runs/031-natural-aligned/segmentation_runs/re86-8af5384d_p0_requests.jsonl:21；analysis_step=7，snapshot_action=31。

```json
[
  {
    "field": "runs",
    "kind": "subscript_load",
    "code_line": 5,
    "expression": "n['runs']",
    "enclosing_scopes": []
  },
  {
    "field": "runs",
    "kind": "subscript_load",
    "code_line": 3,
    "expression": "n['runs']",
    "enclosing_scopes": [
      "For"
    ]
  },
  {
    "field": "runs",
    "kind": "subscript_load",
    "code_line": 3,
    "expression": "n['runs']",
    "enclosing_scopes": [
      "For"
    ]
  }
]
```

## re86-8af5384d · segmentation_runs · call_c6d8aa36335449f3b32d7d1b

原件：runs/031-natural-aligned/segmentation_runs/re86-8af5384d_p0_requests.jsonl:23；analysis_step=7，snapshot_action=31。

```json
[
  {
    "field": "runs",
    "kind": "subscript_load",
    "code_line": 7,
    "expression": "n['runs']",
    "enclosing_scopes": [
      "For",
      "If",
      "For",
      "FunctionDef"
    ]
  },
  {
    "field": "runs",
    "kind": "subscript_load",
    "code_line": 31,
    "expression": "n['runs']",
    "enclosing_scopes": [
      "FunctionDef"
    ]
  }
]
```

## re86-8af5384d · segmentation_runs · call_84e9c6d69a4b45b699f9dac7

原件：runs/031-natural-aligned/segmentation_runs/re86-8af5384d_p0_requests.jsonl:25；analysis_step=8，snapshot_action=34。

```json
[
  {
    "field": "runs",
    "kind": "subscript_load",
    "code_line": 7,
    "expression": "n['runs']",
    "enclosing_scopes": [
      "For",
      "For",
      "FunctionDef"
    ]
  },
  {
    "field": "runs",
    "kind": "subscript_load",
    "code_line": 32,
    "expression": "n['runs']",
    "enclosing_scopes": [
      "For"
    ]
  }
]
```

## re86-8af5384d · segmentation_runs · call_0a06c4901ca64e5688ab77c7

原件：runs/031-natural-aligned/segmentation_runs/re86-8af5384d_p0_requests.jsonl:27；analysis_step=9，snapshot_action=44。

```json
[
  {
    "field": "runs",
    "kind": "subscript_load",
    "code_line": 3,
    "expression": "n['runs']",
    "enclosing_scopes": []
  },
  {
    "field": "runs",
    "kind": "subscript_load",
    "code_line": 4,
    "expression": "n['runs']",
    "enclosing_scopes": []
  },
  {
    "field": "runs",
    "kind": "subscript_load",
    "code_line": 5,
    "expression": "n['runs']",
    "enclosing_scopes": []
  }
]
```

## re86-8af5384d · segmentation_runs · call_956c60ccb1eb43f6a91040ae

原件：runs/031-natural-aligned/segmentation_runs/re86-8af5384d_p0_requests.jsonl:29；analysis_step=10，snapshot_action=58。

```json
[
  {
    "field": "runs",
    "kind": "subscript_load",
    "code_line": 2,
    "expression": "n['runs']",
    "enclosing_scopes": []
  },
  {
    "field": "runs",
    "kind": "subscript_load",
    "code_line": 7,
    "expression": "n['runs']",
    "enclosing_scopes": [
      "If"
    ]
  },
  {
    "field": "runs",
    "kind": "subscript_load",
    "code_line": 8,
    "expression": "n['runs']",
    "enclosing_scopes": [
      "If"
    ]
  },
  {
    "field": "runs",
    "kind": "subscript_load",
    "code_line": 9,
    "expression": "n['runs']",
    "enclosing_scopes": [
      "If"
    ]
  }
]
```

## re86-8af5384d · segmentation_runs · call_cbfc26ccc9a24c8faaee6918

原件：runs/031-natural-aligned/segmentation_runs/re86-8af5384d_p0_requests.jsonl:31；analysis_step=10，snapshot_action=58。

```json
[
  {
    "field": "runs",
    "kind": "subscript_load",
    "code_line": 10,
    "expression": "n['runs']",
    "enclosing_scopes": []
  },
  {
    "field": "runs",
    "kind": "subscript_load",
    "code_line": 11,
    "expression": "n['runs']",
    "enclosing_scopes": []
  },
  {
    "field": "runs",
    "kind": "subscript_load",
    "code_line": 8,
    "expression": "c['runs']",
    "enclosing_scopes": [
      "For",
      "If",
      "For"
    ]
  }
]
```

## re86-8af5384d · segmentation_runs · call_4d01e2ec819d4fb88712985a

原件：runs/031-natural-aligned/segmentation_runs/re86-8af5384d_p0_requests.jsonl:33；analysis_step=11，snapshot_action=71。

```json
[
  {
    "field": "runs",
    "kind": "subscript_load",
    "code_line": 2,
    "expression": "n['runs']",
    "enclosing_scopes": []
  },
  {
    "field": "runs",
    "kind": "subscript_load",
    "code_line": 14,
    "expression": "n['runs']",
    "enclosing_scopes": [
      "If"
    ]
  },
  {
    "field": "runs",
    "kind": "subscript_load",
    "code_line": 12,
    "expression": "nodes[ch]['runs']",
    "enclosing_scopes": [
      "For",
      "If",
      "For",
      "If"
    ]
  }
]
```

## re86-8af5384d · segmentation_runs · call_58a9013cc90a40d0aa5ac45d

原件：runs/031-natural-aligned/segmentation_runs/re86-8af5384d_p0_requests.jsonl:35；analysis_step=11，snapshot_action=71。

```json
[
  {
    "field": "runs",
    "kind": "subscript_load",
    "code_line": 5,
    "expression": "n['runs']",
    "enclosing_scopes": [
      "For"
    ]
  },
  {
    "field": "runs",
    "kind": "subscript_load",
    "code_line": 5,
    "expression": "n['runs']",
    "enclosing_scopes": [
      "For"
    ]
  },
  {
    "field": "runs",
    "kind": "subscript_load",
    "code_line": 11,
    "expression": "n['runs']",
    "enclosing_scopes": []
  },
  {
    "field": "runs",
    "kind": "subscript_load",
    "code_line": 12,
    "expression": "n['runs']",
    "enclosing_scopes": []
  },
  {
    "field": "runs",
    "kind": "subscript_load",
    "code_line": 10,
    "expression": "nodes[ch]['runs']",
    "enclosing_scopes": [
      "For",
      "If",
      "For"
    ]
  }
]
```

## re86-8af5384d · segmentation_runs · call_834725449ffe46adac596273

原件：runs/031-natural-aligned/segmentation_runs/re86-8af5384d_p0_requests.jsonl:37；analysis_step=11，snapshot_action=71。

```json
[
  {
    "field": "runs",
    "kind": "subscript_load",
    "code_line": 5,
    "expression": "n['runs']",
    "enclosing_scopes": [
      "For",
      "If",
      "For"
    ]
  }
]
```

## re86-8af5384d · segmentation_runs · call_3526f7e86b9f4338bedd3a00

原件：runs/031-natural-aligned/segmentation_runs/re86-8af5384d_p0_requests.jsonl:39；analysis_step=11，snapshot_action=71。

```json
[
  {
    "field": "runs",
    "kind": "subscript_load",
    "code_line": 5,
    "expression": "n['runs']",
    "enclosing_scopes": [
      "For",
      "If",
      "For"
    ]
  }
]
```

## re86-8af5384d · segmentation_runs · call_8839b05e81e84f42b376197e

原件：runs/031-natural-aligned/segmentation_runs/re86-8af5384d_p0_requests.jsonl:47；analysis_step=12，snapshot_action=72。

```json
[
  {
    "field": "runs",
    "kind": "subscript_load",
    "code_line": 16,
    "expression": "n['runs']",
    "enclosing_scopes": []
  },
  {
    "field": "runs",
    "kind": "subscript_load",
    "code_line": 5,
    "expression": "n['runs']",
    "enclosing_scopes": [
      "If",
      "For",
      "FunctionDef"
    ]
  },
  {
    "field": "runs",
    "kind": "subscript_load",
    "code_line": 13,
    "expression": "nodes[ch]['runs']",
    "enclosing_scopes": [
      "For",
      "If",
      "For",
      "FunctionDef"
    ]
  }
]
```

## re86-8af5384d · segmentation_runs · call_d0001258ef454e99aa38ec01

原件：runs/031-natural-aligned/segmentation_runs/re86-8af5384d_p0_requests.jsonl:49；analysis_step=13，snapshot_action=86。

```json
[
  {
    "field": "runs",
    "kind": "subscript_load",
    "code_line": 3,
    "expression": "n['runs']",
    "enclosing_scopes": []
  },
  {
    "field": "runs",
    "kind": "subscript_load",
    "code_line": 5,
    "expression": "n['runs']",
    "enclosing_scopes": []
  }
]
```

## re86-8af5384d · segmentation_runs · call_adbcb756ade842f2879b46e1

原件：runs/031-natural-aligned/segmentation_runs/re86-8af5384d_p0_requests.jsonl:51；analysis_step=13，snapshot_action=86。

```json
[
  {
    "field": "runs",
    "kind": "subscript_load",
    "code_line": 9,
    "expression": "n['runs']",
    "enclosing_scopes": [
      "For",
      "If",
      "For",
      "FunctionDef"
    ]
  },
  {
    "field": "runs",
    "kind": "subscript_load",
    "code_line": 47,
    "expression": "n['runs']",
    "enclosing_scopes": []
  },
  {
    "field": "runs",
    "kind": "subscript_load",
    "code_line": 3,
    "expression": "n['runs']",
    "enclosing_scopes": [
      "FunctionDef"
    ]
  }
]
```

## re86-8af5384d · segmentation_runs · call_181a6daece1e4800bda681ea

原件：runs/031-natural-aligned/segmentation_runs/re86-8af5384d_p0_requests.jsonl:53；analysis_step=14，snapshot_action=119。

```json
[
  {
    "field": "runs",
    "kind": "subscript_load",
    "code_line": 3,
    "expression": "n['runs']",
    "enclosing_scopes": [
      "FunctionDef"
    ]
  },
  {
    "field": "runs",
    "kind": "subscript_load",
    "code_line": 37,
    "expression": "n['runs']",
    "enclosing_scopes": []
  }
]
```

## re86-8af5384d · segmentation_runs · call_78e9f94a6e954359a7cf5a3a

原件：runs/031-natural-aligned/segmentation_runs/re86-8af5384d_p0_requests.jsonl:55；analysis_step=14，snapshot_action=119。

```json
[
  {
    "field": "runs",
    "kind": "subscript_load",
    "code_line": 9,
    "expression": "n['runs']",
    "enclosing_scopes": []
  },
  {
    "field": "runs",
    "kind": "subscript_load",
    "code_line": 4,
    "expression": "n['runs']",
    "enclosing_scopes": [
      "If",
      "For"
    ]
  },
  {
    "field": "runs",
    "kind": "subscript_load",
    "code_line": 4,
    "expression": "n['runs']",
    "enclosing_scopes": [
      "If",
      "For"
    ]
  },
  {
    "field": "runs",
    "kind": "subscript_load",
    "code_line": 8,
    "expression": "n['runs']",
    "enclosing_scopes": [
      "If",
      "For"
    ]
  }
]
```

## re86-8af5384d · segmentation_runs · call_5b92f27d82b14717be7d81bc

原件：runs/031-natural-aligned/segmentation_runs/re86-8af5384d_p0_requests.jsonl:59；analysis_step=15，snapshot_action=134。

```json
[
  {
    "field": "runs",
    "kind": "subscript_load",
    "code_line": 6,
    "expression": "n['runs']",
    "enclosing_scopes": []
  }
]
```

## re86-8af5384d · segmentation_runs · call_9d7a46aad1fc446e9c0fd3ea

原件：runs/031-natural-aligned/segmentation_runs/re86-8af5384d_p0_requests.jsonl:63；analysis_step=16，snapshot_action=143。

```json
[
  {
    "field": "runs",
    "kind": "subscript_load",
    "code_line": 8,
    "expression": "n['runs']",
    "enclosing_scopes": []
  }
]
```

## re86-8af5384d · segmentation_runs · call_dd16a4cfe4794c16a7013b9f

原件：runs/031-natural-aligned/segmentation_runs/re86-8af5384d_p0_requests.jsonl:65；analysis_step=16，snapshot_action=143。

```json
[
  {
    "field": "runs",
    "kind": "subscript_load",
    "code_line": 5,
    "expression": "n['runs']",
    "enclosing_scopes": [
      "For",
      "For",
      "FunctionDef"
    ]
  }
]
```

## re86-8af5384d · segmentation_runs · call_bdf0b36d15c84ba2af6d40ef

原件：runs/031-natural-aligned/segmentation_runs/re86-8af5384d_p0_requests.jsonl:67；analysis_step=17，snapshot_action=162。

```json
[
  {
    "field": "runs",
    "kind": "subscript_load",
    "code_line": 5,
    "expression": "n['runs']",
    "enclosing_scopes": []
  }
]
```

## r11l-495a7899 · segmentation_runs · call_6dd36afa3a8d42849e884671

原件：runs/031-natural-aligned/segmentation_runs/r11l-495a7899_p0_requests.jsonl:3；analysis_step=1，snapshot_action=1。

```json
[
  {
    "field": "runs",
    "kind": "subscript_load",
    "code_line": 7,
    "expression": "n['runs']",
    "enclosing_scopes": [
      "For"
    ]
  }
]
```

## r11l-495a7899 · segmentation_runs · call_eacb6256c5234416b7a47e80

原件：runs/031-natural-aligned/segmentation_runs/r11l-495a7899_p0_requests.jsonl:9；analysis_step=2，snapshot_action=2。

```json
[
  {
    "field": "runs",
    "kind": "subscript_load",
    "code_line": 7,
    "expression": "n['runs']",
    "enclosing_scopes": [
      "If",
      "For"
    ]
  }
]
```

## r11l-495a7899 · segmentation_runs · call_ea2e87fc86fe46489b764b61

原件：runs/031-natural-aligned/segmentation_runs/r11l-495a7899_p0_requests.jsonl:21；analysis_step=5，snapshot_action=7。

```json
[
  {
    "field": "runs",
    "kind": "subscript_load",
    "code_line": 5,
    "expression": "n['runs']",
    "enclosing_scopes": [
      "If",
      "For"
    ]
  }
]
```

## r11l-495a7899 · segmentation_runs · call_77ba881468614ce581391be9

原件：runs/031-natural-aligned/segmentation_runs/r11l-495a7899_p0_requests.jsonl:27；analysis_step=6，snapshot_action=8。

```json
[
  {
    "field": "runs",
    "kind": "subscript_load",
    "code_line": 6,
    "expression": "n['runs']",
    "enclosing_scopes": [
      "If",
      "For"
    ]
  }
]
```

## r11l-495a7899 · segmentation_runs · call_6434be55cd824f34adc9cda4

原件：runs/031-natural-aligned/segmentation_runs/r11l-495a7899_p0_requests.jsonl:37；analysis_step=7，snapshot_action=9。

```json
[
  {
    "field": "runs",
    "kind": "subscript_load",
    "code_line": 10,
    "expression": "n['runs']",
    "enclosing_scopes": [
      "For",
      "If",
      "For",
      "FunctionDef"
    ]
  }
]
```

## r11l-495a7899 · segmentation_runs · call_a59813a6e9f145bf81f4bb27

原件：runs/031-natural-aligned/segmentation_runs/r11l-495a7899_p0_requests.jsonl:39；analysis_step=7，snapshot_action=9。

```json
[
  {
    "field": "runs",
    "kind": "subscript_load",
    "code_line": 10,
    "expression": "n['runs']",
    "enclosing_scopes": [
      "For",
      "If",
      "For",
      "FunctionDef"
    ]
  }
]
```

## r11l-495a7899 · segmentation_runs · call_62e30c891c0a492e94c2507b

原件：runs/031-natural-aligned/segmentation_runs/r11l-495a7899_p0_requests.jsonl:55；analysis_step=8，snapshot_action=13。

```json
[
  {
    "field": "runs",
    "kind": "subscript_load",
    "code_line": 6,
    "expression": "n['runs']",
    "enclosing_scopes": [
      "If",
      "For"
    ]
  }
]
```

## r11l-495a7899 · segmentation_runs · call_aa4bcd60e4914041921fbb6a

原件：runs/031-natural-aligned/segmentation_runs/r11l-495a7899_p0_requests.jsonl:57；analysis_step=8，snapshot_action=13。

```json
[
  {
    "field": "runs",
    "kind": "subscript_load",
    "code_line": 6,
    "expression": "n['runs']",
    "enclosing_scopes": [
      "For",
      "If",
      "For"
    ]
  }
]
```

## r11l-495a7899 · segmentation_runs · call_bdbbba6fd7b14c91b2f2a691

原件：runs/031-natural-aligned/segmentation_runs/r11l-495a7899_p0_requests.jsonl:59；analysis_step=8，snapshot_action=13。

```json
[
  {
    "field": "runs",
    "kind": "subscript_load",
    "code_line": 9,
    "expression": "n['runs']",
    "enclosing_scopes": [
      "For",
      "If",
      "For",
      "FunctionDef"
    ]
  }
]
```

## r11l-495a7899 · segmentation_runs · call_da7b7b70b22842ce84d8e910

原件：runs/031-natural-aligned/segmentation_runs/r11l-495a7899_p0_requests.jsonl:65；analysis_step=9，snapshot_action=19。

```json
[
  {
    "field": "runs",
    "kind": "subscript_load",
    "code_line": 5,
    "expression": "n['runs']",
    "enclosing_scopes": [
      "If",
      "For"
    ]
  },
  {
    "field": "runs",
    "kind": "subscript_load",
    "code_line": 5,
    "expression": "n['runs']",
    "enclosing_scopes": [
      "If",
      "For"
    ]
  }
]
```

## sp80-589a99af · segmentation_runs · call_92a0b27923aa4b44ba596d6a

原件：runs/031-natural-aligned/segmentation_runs/sp80-589a99af_p0_requests.jsonl:3；analysis_step=1，snapshot_action=1。

```json
[
  {
    "field": "runs",
    "kind": "subscript_load",
    "code_line": 6,
    "expression": "n['runs']",
    "enclosing_scopes": [
      "For"
    ]
  }
]
```

## sp80-589a99af · segmentation_runs · call_e30416cc2c8a49b8be440ba8

原件：runs/031-natural-aligned/segmentation_runs/sp80-589a99af_p0_requests.jsonl:7；analysis_step=2，snapshot_action=2。

```json
[
  {
    "field": "runs",
    "kind": "subscript_load",
    "code_line": 4,
    "expression": "n['runs']",
    "enclosing_scopes": [
      "For"
    ]
  },
  {
    "field": "runs",
    "kind": "subscript_load",
    "code_line": 4,
    "expression": "n['runs']",
    "enclosing_scopes": [
      "For"
    ]
  }
]
```

## sp80-589a99af · segmentation_runs · call_043da88967404b98ad079d6c

原件：runs/031-natural-aligned/segmentation_runs/sp80-589a99af_p0_requests.jsonl:15；analysis_step=4，snapshot_action=4。

```json
[
  {
    "field": "runs",
    "kind": "subscript_load",
    "code_line": 6,
    "expression": "n['runs']",
    "enclosing_scopes": [
      "If",
      "For"
    ]
  }
]
```

## sp80-589a99af · segmentation_runs · call_9d697ecd6b69467182eb1066

原件：runs/031-natural-aligned/segmentation_runs/sp80-589a99af_p0_requests.jsonl:17；analysis_step=5，snapshot_action=6。

```json
[
  {
    "field": "runs",
    "kind": "subscript_load",
    "code_line": 6,
    "expression": "n['runs']",
    "enclosing_scopes": [
      "If",
      "For"
    ]
  }
]
```

## sp80-589a99af · segmentation_runs · call_ad1dde9f4a03499baa4a03ad

原件：runs/031-natural-aligned/segmentation_runs/sp80-589a99af_p0_requests.jsonl:19；analysis_step=5，snapshot_action=6。

```json
[
  {
    "field": "runs",
    "kind": "subscript_load",
    "code_line": 7,
    "expression": "n['runs']",
    "enclosing_scopes": [
      "If",
      "For",
      "For"
    ]
  }
]
```

## sp80-589a99af · segmentation_runs · call_aa54c3300cc34469a4d1fc8c

原件：runs/031-natural-aligned/segmentation_runs/sp80-589a99af_p0_requests.jsonl:21；analysis_step=5，snapshot_action=6。

```json
[
  {
    "field": "runs",
    "kind": "subscript_load",
    "code_line": 7,
    "expression": "n['runs']",
    "enclosing_scopes": [
      "For",
      "If",
      "For"
    ]
  }
]
```

## sp80-589a99af · segmentation_runs · call_5a3685c533cc4a66b0d79c1c

原件：runs/031-natural-aligned/segmentation_runs/sp80-589a99af_p0_requests.jsonl:23；analysis_step=6，snapshot_action=8。

```json
[
  {
    "field": "runs",
    "kind": "subscript_load",
    "code_line": 11,
    "expression": "n['runs']",
    "enclosing_scopes": [
      "If",
      "For",
      "For"
    ]
  },
  {
    "field": "runs",
    "kind": "subscript_load",
    "code_line": 4,
    "expression": "n['runs']",
    "enclosing_scopes": [
      "If",
      "For"
    ]
  }
]
```

## sp80-589a99af · segmentation_runs · call_c8edd2e038ba4bccb61dafc7

原件：runs/031-natural-aligned/segmentation_runs/sp80-589a99af_p0_requests.jsonl:25；analysis_step=6，snapshot_action=8。

```json
[
  {
    "field": "runs",
    "kind": "subscript_load",
    "code_line": 5,
    "expression": "n['runs']",
    "enclosing_scopes": [
      "For"
    ]
  }
]
```

## sp80-589a99af · segmentation_runs · call_30d1ad936a2746248e71e920

原件：runs/031-natural-aligned/segmentation_runs/sp80-589a99af_p0_requests.jsonl:27；analysis_step=7，snapshot_action=12。

```json
[
  {
    "field": "runs",
    "kind": "subscript_load",
    "code_line": 6,
    "expression": "n['runs']",
    "enclosing_scopes": [
      "If",
      "For",
      "FunctionDef"
    ]
  }
]
```

## sp80-589a99af · segmentation_runs · call_f02829bf753543aea11c6932

原件：runs/031-natural-aligned/segmentation_runs/sp80-589a99af_p0_requests.jsonl:31；analysis_step=8，snapshot_action=15。

```json
[
  {
    "field": "runs",
    "kind": "subscript_load",
    "code_line": 11,
    "expression": "n['runs']",
    "enclosing_scopes": [
      "If",
      "For",
      "For"
    ]
  }
]
```

## sp80-589a99af · segmentation_runs · call_354ccebfae3a41fc84d25069

原件：runs/031-natural-aligned/segmentation_runs/sp80-589a99af_p0_requests.jsonl:33；analysis_step=8，snapshot_action=15。

```json
[
  {
    "field": "runs",
    "kind": "subscript_load",
    "code_line": 6,
    "expression": "n['runs']",
    "enclosing_scopes": [
      "If",
      "For",
      "For"
    ]
  }
]
```

## sp80-589a99af · segmentation_runs · call_e5069c0b77884914b2a0d6e8

原件：runs/031-natural-aligned/segmentation_runs/sp80-589a99af_p0_requests.jsonl:35；analysis_step=9，snapshot_action=17。

```json
[
  {
    "field": "runs",
    "kind": "subscript_load",
    "code_line": 10,
    "expression": "n['runs']",
    "enclosing_scopes": [
      "If",
      "For",
      "For"
    ]
  },
  {
    "field": "runs",
    "kind": "subscript_load",
    "code_line": 12,
    "expression": "n['runs']",
    "enclosing_scopes": [
      "If",
      "If",
      "For",
      "For"
    ]
  }
]
```

## sp80-589a99af · segmentation_runs · call_9b5961592570455ebae5c6bb

原件：runs/031-natural-aligned/segmentation_runs/sp80-589a99af_p0_requests.jsonl:37；analysis_step=9，snapshot_action=17。

```json
[
  {
    "field": "runs",
    "kind": "subscript_load",
    "code_line": 7,
    "expression": "n['runs']",
    "enclosing_scopes": [
      "For",
      "If",
      "For",
      "For"
    ]
  }
]
```

## tu93-0768757b · segmentation_runs · call_1ee0a2ff77744772a9b5ba8e

原件：runs/031-natural-aligned/segmentation_runs/tu93-0768757b_p0_requests.jsonl:3；analysis_step=1，snapshot_action=1。

```json
[
  {
    "field": "runs",
    "kind": "subscript_load",
    "code_line": 6,
    "expression": "n['runs']",
    "enclosing_scopes": [
      "For"
    ]
  }
]
```

## tu93-0768757b · segmentation_runs · call_c2c9371c9e904642b03e415b

原件：runs/031-natural-aligned/segmentation_runs/tu93-0768757b_p0_requests.jsonl:17；analysis_step=4，snapshot_action=19。

```json
[
  {
    "field": "runs",
    "kind": "subscript_load",
    "code_line": 4,
    "expression": "n['runs']",
    "enclosing_scopes": [
      "If",
      "For"
    ]
  }
]
```

## tu93-0768757b · segmentation_runs · call_12b56025a71d4192b6032337

原件：runs/031-natural-aligned/segmentation_runs/tu93-0768757b_p0_requests.jsonl:27；analysis_step=5，snapshot_action=24。

```json
[
  {
    "field": "runs",
    "kind": "subscript_load",
    "code_line": 5,
    "expression": "n['runs']",
    "enclosing_scopes": [
      "If",
      "For",
      "FunctionDef"
    ]
  }
]
```

## tu93-0768757b · segmentation_runs · call_a930711b83644f0cae23a9b6

原件：runs/031-natural-aligned/segmentation_runs/tu93-0768757b_p0_requests.jsonl:29；analysis_step=6，snapshot_action=27。

```json
[
  {
    "field": "runs",
    "kind": "subscript_load",
    "code_line": 5,
    "expression": "n['runs']",
    "enclosing_scopes": [
      "If",
      "For",
      "FunctionDef"
    ]
  },
  {
    "field": "runs",
    "kind": "subscript_load",
    "code_line": 5,
    "expression": "n['runs']",
    "enclosing_scopes": [
      "If",
      "For",
      "FunctionDef"
    ]
  },
  {
    "field": "runs",
    "kind": "subscript_load",
    "code_line": 5,
    "expression": "n['runs']",
    "enclosing_scopes": [
      "If",
      "For",
      "FunctionDef"
    ]
  },
  {
    "field": "runs",
    "kind": "subscript_load",
    "code_line": 5,
    "expression": "n['runs']",
    "enclosing_scopes": [
      "If",
      "For",
      "FunctionDef"
    ]
  }
]
```

## tu93-0768757b · segmentation_runs · call_2d993bae242d4602acb4b342

原件：runs/031-natural-aligned/segmentation_runs/tu93-0768757b_p0_requests.jsonl:43；analysis_step=10，snapshot_action=37。

```json
[
  {
    "field": "runs",
    "kind": "subscript_load",
    "code_line": 3,
    "expression": "n['runs']",
    "enclosing_scopes": [
      "If",
      "For"
    ]
  }
]
```

## tu93-0768757b · segmentation_runs · call_8583106ffd424c3eb0f31b4c

原件：runs/031-natural-aligned/segmentation_runs/tu93-0768757b_p0_requests.jsonl:45；analysis_step=11，snapshot_action=42。

```json
[
  {
    "field": "runs",
    "kind": "subscript_load",
    "code_line": 14,
    "expression": "n['runs']",
    "enclosing_scopes": [
      "If",
      "For",
      "For"
    ]
  }
]
```

## tu93-0768757b · segmentation_runs · call_46a81c107343419bb520bfce

原件：runs/031-natural-aligned/segmentation_runs/tu93-0768757b_p0_requests.jsonl:49；analysis_step=13，snapshot_action=52。

```json
[
  {
    "field": "runs",
    "kind": "subscript_load",
    "code_line": 4,
    "expression": "n['runs']",
    "enclosing_scopes": [
      "If",
      "For"
    ]
  }
]
```

## tu93-0768757b · segmentation_runs · call_5952161cfec6479eb01e710d

原件：runs/031-natural-aligned/segmentation_runs/tu93-0768757b_p0_requests.jsonl:51；analysis_step=14，snapshot_action=53。

```json
[
  {
    "field": "runs",
    "kind": "subscript_load",
    "code_line": 4,
    "expression": "n['runs']",
    "enclosing_scopes": [
      "If",
      "For"
    ]
  }
]
```

## tu93-0768757b · segmentation_runs · call_5f29a8c125e94dcba566859a

原件：runs/031-natural-aligned/segmentation_runs/tu93-0768757b_p0_requests.jsonl:55；analysis_step=16，snapshot_action=61。

```json
[
  {
    "field": "runs",
    "kind": "subscript_load",
    "code_line": 6,
    "expression": "n['runs']",
    "enclosing_scopes": [
      "If",
      "For",
      "If"
    ]
  }
]
```

## tu93-0768757b · segmentation_runs · call_89c89b1016654729a71af1dd

原件：runs/031-natural-aligned/segmentation_runs/tu93-0768757b_p0_requests.jsonl:57；analysis_step=16，snapshot_action=61。

```json
[
  {
    "field": "runs",
    "kind": "subscript_load",
    "code_line": 6,
    "expression": "n['runs']",
    "enclosing_scopes": [
      "If",
      "For"
    ]
  }
]
```

## tu93-0768757b · segmentation_runs · call_bd2bdae70193401a8da013ff

原件：runs/031-natural-aligned/segmentation_runs/tu93-0768757b_p0_requests.jsonl:61；analysis_step=18，snapshot_action=69。

```json
[
  {
    "field": "runs",
    "kind": "subscript_load",
    "code_line": 5,
    "expression": "n['runs']",
    "enclosing_scopes": [
      "If",
      "For",
      "FunctionDef"
    ]
  },
  {
    "field": "runs",
    "kind": "subscript_load",
    "code_line": 5,
    "expression": "n['runs']",
    "enclosing_scopes": [
      "If",
      "For",
      "FunctionDef"
    ]
  }
]
```

## sc25-635fd71a · segmentation_runs · call_affc092fddea43068509f0f9

原件：runs/031-natural-aligned/segmentation_runs/sc25-635fd71a_p0_requests.jsonl:3；analysis_step=1，snapshot_action=1。

```json
[
  {
    "field": "runs",
    "kind": "subscript_load",
    "code_line": 4,
    "expression": "n['runs']",
    "enclosing_scopes": [
      "For"
    ]
  },
  {
    "field": "boundary",
    "kind": "subscript_load",
    "code_line": 4,
    "expression": "n['boundary']",
    "enclosing_scopes": [
      "For"
    ]
  }
]
```

## sc25-635fd71a · segmentation_runs · call_9134be6b60564b39bc3beff1

原件：runs/031-natural-aligned/segmentation_runs/sc25-635fd71a_p0_requests.jsonl:11；analysis_step=4，snapshot_action=4。

```json
[
  {
    "field": "runs",
    "kind": "subscript_load",
    "code_line": 12,
    "expression": "n['runs']",
    "enclosing_scopes": [
      "For",
      "For",
      "FunctionDef"
    ]
  }
]
```

## sc25-635fd71a · segmentation_runs · call_79ed8fe0104448988421593c

原件：runs/031-natural-aligned/segmentation_runs/sc25-635fd71a_p0_requests.jsonl:13；analysis_step=5，snapshot_action=5。

```json
[
  {
    "field": "runs",
    "kind": "subscript_load",
    "code_line": 4,
    "expression": "n['runs']",
    "enclosing_scopes": [
      "If",
      "For"
    ]
  },
  {
    "field": "runs",
    "kind": "subscript_load",
    "code_line": 4,
    "expression": "n['runs']",
    "enclosing_scopes": [
      "If",
      "For"
    ]
  },
  {
    "field": "runs",
    "kind": "subscript_load",
    "code_line": 3,
    "expression": "n['runs']",
    "enclosing_scopes": [
      "If",
      "For"
    ]
  }
]
```

## sc25-635fd71a · segmentation_runs · call_1340115ae9214a1292a1ff14

原件：runs/031-natural-aligned/segmentation_runs/sc25-635fd71a_p0_requests.jsonl:15；analysis_step=6，snapshot_action=6。

```json
[
  {
    "field": "runs",
    "kind": "subscript_load",
    "code_line": 4,
    "expression": "n['runs']",
    "enclosing_scopes": [
      "For",
      "For",
      "FunctionDef"
    ]
  }
]
```

## sc25-635fd71a · segmentation_runs · call_9d20aeef85044f64bdbb6770

原件：runs/031-natural-aligned/segmentation_runs/sc25-635fd71a_p0_requests.jsonl:17；analysis_step=7，snapshot_action=9。

```json
[
  {
    "field": "runs",
    "kind": "subscript_load",
    "code_line": 4,
    "expression": "n['runs']",
    "enclosing_scopes": [
      "If",
      "For",
      "FunctionDef"
    ]
  },
  {
    "field": "runs",
    "kind": "subscript_load",
    "code_line": 5,
    "expression": "n['runs']",
    "enclosing_scopes": [
      "comprehension",
      "If",
      "For",
      "FunctionDef"
    ]
  }
]
```

## sc25-635fd71a · segmentation_runs · call_f9f46cb533f448c283aefee3

原件：runs/031-natural-aligned/segmentation_runs/sc25-635fd71a_p0_requests.jsonl:23；analysis_step=8，snapshot_action=12。

```json
[
  {
    "field": "runs",
    "kind": "subscript_load",
    "code_line": 4,
    "expression": "n['runs']",
    "enclosing_scopes": [
      "comprehension",
      "If",
      "For"
    ]
  }
]
```

## sc25-635fd71a · segmentation_runs · call_f3d52039a2ca432ba804ab81

原件：runs/031-natural-aligned/segmentation_runs/sc25-635fd71a_p0_requests.jsonl:25；analysis_step=9，snapshot_action=15。

```json
[
  {
    "field": "runs",
    "kind": "subscript_load",
    "code_line": 7,
    "expression": "shaft[0]['runs']",
    "enclosing_scopes": [
      "FunctionDef"
    ]
  },
  {
    "field": "runs",
    "kind": "subscript_load",
    "code_line": 4,
    "expression": "n['runs']",
    "enclosing_scopes": [
      "If",
      "For",
      "FunctionDef"
    ]
  },
  {
    "field": "runs",
    "kind": "subscript_load",
    "code_line": 4,
    "expression": "n['runs']",
    "enclosing_scopes": [
      "If",
      "For",
      "FunctionDef"
    ]
  },
  {
    "field": "runs",
    "kind": "subscript_load",
    "code_line": 5,
    "expression": "n['runs']",
    "enclosing_scopes": [
      "comprehension",
      "If",
      "For",
      "FunctionDef"
    ]
  },
  {
    "field": "runs",
    "kind": "subscript_load",
    "code_line": 6,
    "expression": "n['runs']",
    "enclosing_scopes": [
      "comprehension",
      "FunctionDef"
    ]
  }
]
```

## sc25-635fd71a · segmentation_runs · call_4bcefd1156ab41b0aeb0b30c

原件：runs/031-natural-aligned/segmentation_runs/sc25-635fd71a_p0_requests.jsonl:31；analysis_step=11，snapshot_action=29。

```json
[
  {
    "field": "runs",
    "kind": "subscript_load",
    "code_line": 4,
    "expression": "n['runs']",
    "enclosing_scopes": [
      "comprehension",
      "If",
      "For"
    ]
  }
]
```

## sc25-635fd71a · segmentation_runs · call_a63b25e8dcc744a0ac2ceb3d

原件：runs/031-natural-aligned/segmentation_runs/sc25-635fd71a_p0_requests.jsonl:37；analysis_step=13，snapshot_action=34。

```json
[
  {
    "field": "runs",
    "kind": "subscript_load",
    "code_line": 4,
    "expression": "n['runs']",
    "enclosing_scopes": []
  }
]
```

## sc25-635fd71a · segmentation_runs · call_e0971e4bac8843aea6f91a4c

原件：runs/031-natural-aligned/segmentation_runs/sc25-635fd71a_p0_requests.jsonl:45；analysis_step=15，snapshot_action=41。

```json
[
  {
    "field": "runs",
    "kind": "subscript_load",
    "code_line": 7,
    "expression": "n['runs']",
    "enclosing_scopes": [
      "comprehension",
      "If",
      "For"
    ]
  }
]
```

## sc25-635fd71a · segmentation_runs · call_baf0ce47b5ad45e2920e55b5

原件：runs/031-natural-aligned/segmentation_runs/sc25-635fd71a_p0_requests.jsonl:49；analysis_step=16，snapshot_action=42。

```json
[
  {
    "field": "runs",
    "kind": "subscript_load",
    "code_line": 4,
    "expression": "n['runs']",
    "enclosing_scopes": [
      "comprehension",
      "If",
      "For"
    ]
  }
]
```

## sc25-635fd71a · segmentation_runs · call_1de02e2c011144059d627c5c

原件：runs/031-natural-aligned/segmentation_runs/sc25-635fd71a_p0_requests.jsonl:51；analysis_step=17，snapshot_action=45。

```json
[
  {
    "field": "runs",
    "kind": "subscript_load",
    "code_line": 4,
    "expression": "n['runs']",
    "enclosing_scopes": [
      "For",
      "For",
      "FunctionDef"
    ]
  }
]
```

## sc25-635fd71a · segmentation_runs · call_e82f3891d25d4f2e99205b8a

原件：runs/031-natural-aligned/segmentation_runs/sc25-635fd71a_p0_requests.jsonl:55；analysis_step=18，snapshot_action=47。

```json
[
  {
    "field": "runs",
    "kind": "subscript_load",
    "code_line": 4,
    "expression": "n['runs']",
    "enclosing_scopes": [
      "comprehension",
      "If",
      "For"
    ]
  }
]
```

## sc25-635fd71a · segmentation_runs · call_d5759fb9b08343afaf5712eb

原件：runs/031-natural-aligned/segmentation_runs/sc25-635fd71a_p0_requests.jsonl:57；analysis_step=19，snapshot_action=50。

```json
[
  {
    "field": "runs",
    "kind": "subscript_load",
    "code_line": 7,
    "expression": "n['runs']",
    "enclosing_scopes": [
      "If",
      "For"
    ]
  },
  {
    "field": "runs",
    "kind": "subscript_load",
    "code_line": 7,
    "expression": "n['runs']",
    "enclosing_scopes": [
      "comprehension",
      "If",
      "For"
    ]
  }
]
```

## sc25-635fd71a · segmentation_runs · call_0476152392e1474dade1af03

原件：runs/031-natural-aligned/segmentation_runs/sc25-635fd71a_p0_requests.jsonl:59；analysis_step=19，snapshot_action=50。

```json
[
  {
    "field": "runs",
    "kind": "subscript_load",
    "code_line": 3,
    "expression": "blob['runs']",
    "enclosing_scopes": []
  }
]
```

## sc25-635fd71a · segmentation_runs · call_3d901d8bff40454b8869ed0f

原件：runs/031-natural-aligned/segmentation_runs/sc25-635fd71a_p0_requests.jsonl:61；analysis_step=20，snapshot_action=53。

```json
[
  {
    "field": "runs",
    "kind": "subscript_load",
    "code_line": 4,
    "expression": "n['runs']",
    "enclosing_scopes": [
      "If",
      "For",
      "FunctionDef"
    ]
  },
  {
    "field": "runs",
    "kind": "subscript_load",
    "code_line": 5,
    "expression": "n['runs']",
    "enclosing_scopes": [
      "If",
      "For",
      "FunctionDef"
    ]
  }
]
```

## sc25-635fd71a · segmentation_runs · call_96ef624c36474a0cb5fb790f

原件：runs/031-natural-aligned/segmentation_runs/sc25-635fd71a_p0_requests.jsonl:73；analysis_step=24，snapshot_action=71。

```json
[
  {
    "field": "runs",
    "kind": "subscript_load",
    "code_line": 5,
    "expression": "n['runs']",
    "enclosing_scopes": []
  }
]
```

## sc25-635fd71a · segmentation_runs · call_5fd87971579e4ee484062c54

原件：runs/031-natural-aligned/segmentation_runs/sc25-635fd71a_p0_requests.jsonl:79；analysis_step=26，snapshot_action=80。

```json
[
  {
    "field": "runs",
    "kind": "subscript_load",
    "code_line": 8,
    "expression": "blob['runs']",
    "enclosing_scopes": [
      "For"
    ]
  },
  {
    "field": "runs",
    "kind": "subscript_load",
    "code_line": 4,
    "expression": "n['runs']",
    "enclosing_scopes": [
      "comprehension",
      "If",
      "For"
    ]
  }
]
```

## sc25-635fd71a · segmentation_runs · call_ee7a96eb53834a1c82d51c90

原件：runs/031-natural-aligned/segmentation_runs/sc25-635fd71a_p0_requests.jsonl:83；analysis_step=28，snapshot_action=85。

```json
[
  {
    "field": "runs",
    "kind": "subscript_load",
    "code_line": 6,
    "expression": "n['runs']",
    "enclosing_scopes": []
  }
]
```

## sc25-635fd71a · segmentation_runs · call_25a8e82d5d674afdb890b704

原件：runs/031-natural-aligned/segmentation_runs/sc25-635fd71a_p0_requests.jsonl:85；analysis_step=29，snapshot_action=89。

```json
[
  {
    "field": "runs",
    "kind": "subscript_load",
    "code_line": 8,
    "expression": "n['runs']",
    "enclosing_scopes": []
  }
]
```

## ar25-0c556536 · segmentation_runs · call_63c2c4259a8446ebb93f8672

原件：runs/031-natural-aligned/segmentation_runs/ar25-0c556536_p0_requests.jsonl:3；analysis_step=1，snapshot_action=1。

```json
[
  {
    "field": "runs",
    "kind": "subscript_load",
    "code_line": 3,
    "expression": "n['runs']",
    "enclosing_scopes": [
      "For"
    ]
  }
]
```

## ar25-0c556536 · segmentation_runs · call_8e3398d194f44c75a16dcd43

原件：runs/031-natural-aligned/segmentation_runs/ar25-0c556536_p0_requests.jsonl:7；analysis_step=3，snapshot_action=5。

```json
[
  {
    "field": "runs",
    "kind": "subscript_load",
    "code_line": 20,
    "expression": "n['runs']",
    "enclosing_scopes": [
      "For"
    ]
  },
  {
    "field": "runs",
    "kind": "subscript_load",
    "code_line": 6,
    "expression": "n['runs']",
    "enclosing_scopes": [
      "If",
      "For",
      "FunctionDef"
    ]
  },
  {
    "field": "runs",
    "kind": "subscript_load",
    "code_line": 6,
    "expression": "n['runs']",
    "enclosing_scopes": [
      "If",
      "For",
      "FunctionDef"
    ]
  },
  {
    "field": "runs",
    "kind": "subscript_load",
    "code_line": 6,
    "expression": "n['runs']",
    "enclosing_scopes": [
      "If",
      "For",
      "FunctionDef"
    ]
  },
  {
    "field": "runs",
    "kind": "subscript_load",
    "code_line": 13,
    "expression": "n['runs']",
    "enclosing_scopes": [
      "If",
      "For",
      "FunctionDef"
    ]
  },
  {
    "field": "runs",
    "kind": "subscript_load",
    "code_line": 13,
    "expression": "n['runs']",
    "enclosing_scopes": [
      "If",
      "For",
      "FunctionDef"
    ]
  },
  {
    "field": "runs",
    "kind": "subscript_load",
    "code_line": 13,
    "expression": "n['runs']",
    "enclosing_scopes": [
      "If",
      "For",
      "FunctionDef"
    ]
  }
]
```

## ar25-0c556536 · segmentation_runs · call_f3304bd78380476db7d5aca1

原件：runs/031-natural-aligned/segmentation_runs/ar25-0c556536_p0_requests.jsonl:11；analysis_step=4，snapshot_action=6。

```json
[
  {
    "field": "runs",
    "kind": "subscript_load",
    "code_line": 10,
    "expression": "y['runs']",
    "enclosing_scopes": []
  },
  {
    "field": "runs",
    "kind": "subscript_load",
    "code_line": 10,
    "expression": "y['runs']",
    "enclosing_scopes": []
  },
  {
    "field": "runs",
    "kind": "subscript_load",
    "code_line": 4,
    "expression": "n['runs']",
    "enclosing_scopes": [
      "If",
      "For",
      "FunctionDef"
    ]
  },
  {
    "field": "runs",
    "kind": "subscript_load",
    "code_line": 4,
    "expression": "n['runs']",
    "enclosing_scopes": [
      "If",
      "For",
      "FunctionDef"
    ]
  }
]
```

## ar25-0c556536 · segmentation_runs · call_e716c8b5d4e6428583faa5cf

原件：runs/031-natural-aligned/segmentation_runs/ar25-0c556536_p0_requests.jsonl:13；analysis_step=4，snapshot_action=6。

```json
[
  {
    "field": "runs",
    "kind": "subscript_load",
    "code_line": 2,
    "expression": "n['runs']",
    "enclosing_scopes": [
      "FunctionDef"
    ]
  },
  {
    "field": "runs",
    "kind": "subscript_load",
    "code_line": 2,
    "expression": "n['runs']",
    "enclosing_scopes": [
      "FunctionDef"
    ]
  },
  {
    "field": "runs",
    "kind": "subscript_load",
    "code_line": 2,
    "expression": "n['runs']",
    "enclosing_scopes": [
      "FunctionDef"
    ]
  },
  {
    "field": "runs",
    "kind": "subscript_load",
    "code_line": 2,
    "expression": "n['runs']",
    "enclosing_scopes": [
      "FunctionDef"
    ]
  }
]
```

## ar25-0c556536 · segmentation_runs · call_af3888029cd943408c6c72bc

原件：runs/031-natural-aligned/segmentation_runs/ar25-0c556536_p0_requests.jsonl:15；analysis_step=5，snapshot_action=21。

```json
[
  {
    "field": "runs",
    "kind": "subscript_load",
    "code_line": 4,
    "expression": "n['runs']",
    "enclosing_scopes": [
      "If",
      "For",
      "FunctionDef"
    ]
  },
  {
    "field": "runs",
    "kind": "subscript_load",
    "code_line": 4,
    "expression": "n['runs']",
    "enclosing_scopes": [
      "If",
      "For",
      "FunctionDef"
    ]
  }
]
```

## ar25-0c556536 · segmentation_runs · call_fecc96f3190349baa5030606

原件：runs/031-natural-aligned/segmentation_runs/ar25-0c556536_p0_requests.jsonl:17；analysis_step=5，snapshot_action=21。

```json
[
  {
    "field": "runs",
    "kind": "subscript_load",
    "code_line": 4,
    "expression": "n['runs']",
    "enclosing_scopes": [
      "If",
      "For"
    ]
  },
  {
    "field": "runs",
    "kind": "subscript_load",
    "code_line": 4,
    "expression": "n['runs']",
    "enclosing_scopes": [
      "If",
      "For"
    ]
  },
  {
    "field": "runs",
    "kind": "subscript_load",
    "code_line": 7,
    "expression": "n['runs']",
    "enclosing_scopes": [
      "If",
      "For"
    ]
  },
  {
    "field": "runs",
    "kind": "subscript_load",
    "code_line": 7,
    "expression": "n['runs']",
    "enclosing_scopes": [
      "If",
      "For"
    ]
  }
]
```

## ar25-0c556536 · segmentation_runs · call_ffb4025fe5c541408d79e305

原件：runs/031-natural-aligned/segmentation_runs/ar25-0c556536_p0_requests.jsonl:19；analysis_step=5，snapshot_action=21。

```json
[
  {
    "field": "runs",
    "kind": "subscript_load",
    "code_line": 6,
    "expression": "n['runs']",
    "enclosing_scopes": [
      "For",
      "FunctionDef"
    ]
  },
  {
    "field": "runs",
    "kind": "subscript_load",
    "code_line": 3,
    "expression": "n['runs']",
    "enclosing_scopes": [
      "comprehension",
      "FunctionDef"
    ]
  },
  {
    "field": "runs",
    "kind": "subscript_load",
    "code_line": 3,
    "expression": "n['runs']",
    "enclosing_scopes": [
      "comprehension",
      "FunctionDef"
    ]
  },
  {
    "field": "runs",
    "kind": "subscript_load",
    "code_line": 4,
    "expression": "n['runs']",
    "enclosing_scopes": [
      "comprehension",
      "FunctionDef"
    ]
  },
  {
    "field": "runs",
    "kind": "subscript_load",
    "code_line": 4,
    "expression": "n['runs']",
    "enclosing_scopes": [
      "comprehension",
      "FunctionDef"
    ]
  }
]
```

## ar25-0c556536 · segmentation_runs · call_6451f0deae6047d69e974697

原件：runs/031-natural-aligned/segmentation_runs/ar25-0c556536_p0_requests.jsonl:21；analysis_step=6，snapshot_action=22。

```json
[
  {
    "field": "runs",
    "kind": "subscript_load",
    "code_line": 4,
    "expression": "n['runs']",
    "enclosing_scopes": [
      "If",
      "For",
      "FunctionDef"
    ]
  },
  {
    "field": "runs",
    "kind": "subscript_load",
    "code_line": 4,
    "expression": "n['runs']",
    "enclosing_scopes": [
      "comprehension",
      "If",
      "For",
      "FunctionDef"
    ]
  }
]
```

## ar25-0c556536 · segmentation_runs · call_1138f7ef820149b99aea2191

原件：runs/031-natural-aligned/segmentation_runs/ar25-0c556536_p0_requests.jsonl:23；analysis_step=7，snapshot_action=23。

```json
[
  {
    "field": "runs",
    "kind": "subscript_load",
    "code_line": 12,
    "expression": "n['runs']",
    "enclosing_scopes": []
  }
]
```

## ar25-0c556536 · segmentation_runs · call_6b6e9ec59e0d4cb29a4fd429

原件：runs/031-natural-aligned/segmentation_runs/ar25-0c556536_p0_requests.jsonl:25；analysis_step=8，snapshot_action=24。

```json
[
  {
    "field": "runs",
    "kind": "subscript_load",
    "code_line": 5,
    "expression": "n['runs']",
    "enclosing_scopes": [
      "If",
      "For",
      "FunctionDef"
    ]
  },
  {
    "field": "runs",
    "kind": "subscript_load",
    "code_line": 5,
    "expression": "n['runs']",
    "enclosing_scopes": [
      "If",
      "For",
      "FunctionDef"
    ]
  },
  {
    "field": "runs",
    "kind": "subscript_load",
    "code_line": 5,
    "expression": "n['runs']",
    "enclosing_scopes": [
      "comprehension",
      "If",
      "For",
      "FunctionDef"
    ]
  },
  {
    "field": "runs",
    "kind": "subscript_load",
    "code_line": 5,
    "expression": "n['runs']",
    "enclosing_scopes": [
      "comprehension",
      "If",
      "For",
      "FunctionDef"
    ]
  }
]
```

## ar25-0c556536 · segmentation_runs · call_d69958803faf45c1ac5188df

原件：runs/031-natural-aligned/segmentation_runs/ar25-0c556536_p0_requests.jsonl:39；analysis_step=12，snapshot_action=30。

```json
[
  {
    "field": "runs",
    "kind": "subscript_load",
    "code_line": 5,
    "expression": "n['runs']",
    "enclosing_scopes": [
      "comprehension",
      "If",
      "For",
      "FunctionDef"
    ]
  },
  {
    "field": "runs",
    "kind": "subscript_load",
    "code_line": 5,
    "expression": "n['runs']",
    "enclosing_scopes": [
      "comprehension",
      "If",
      "For",
      "FunctionDef"
    ]
  },
  {
    "field": "runs",
    "kind": "subscript_load",
    "code_line": 7,
    "expression": "n['runs']",
    "enclosing_scopes": [
      "If",
      "For",
      "FunctionDef"
    ]
  },
  {
    "field": "runs",
    "kind": "subscript_load",
    "code_line": 7,
    "expression": "n['runs']",
    "enclosing_scopes": [
      "If",
      "For",
      "FunctionDef"
    ]
  }
]
```

## ar25-0c556536 · segmentation_runs · call_6b77543c10dd4c4d9d502668

原件：runs/031-natural-aligned/segmentation_runs/ar25-0c556536_p0_requests.jsonl:43；analysis_step=14，snapshot_action=38。

```json
[
  {
    "field": "runs",
    "kind": "subscript_load",
    "code_line": 4,
    "expression": "n['runs']",
    "enclosing_scopes": [
      "If",
      "For",
      "FunctionDef"
    ]
  },
  {
    "field": "runs",
    "kind": "subscript_load",
    "code_line": 5,
    "expression": "n['runs']",
    "enclosing_scopes": [
      "If",
      "For",
      "FunctionDef"
    ]
  },
  {
    "field": "runs",
    "kind": "subscript_load",
    "code_line": 4,
    "expression": "n['runs']",
    "enclosing_scopes": [
      "comprehension",
      "If",
      "For",
      "FunctionDef"
    ]
  },
  {
    "field": "runs",
    "kind": "subscript_load",
    "code_line": 5,
    "expression": "n['runs']",
    "enclosing_scopes": [
      "comprehension",
      "If",
      "For",
      "FunctionDef"
    ]
  }
]
```

## ar25-0c556536 · segmentation_runs · call_9ccea8f41c0e43e9bdc8723d

原件：runs/031-natural-aligned/segmentation_runs/ar25-0c556536_p0_requests.jsonl:45；analysis_step=14，snapshot_action=38。

```json
[
  {
    "field": "runs",
    "kind": "subscript_load",
    "code_line": 8,
    "expression": "n['runs']",
    "enclosing_scopes": [
      "If",
      "For"
    ]
  },
  {
    "field": "runs",
    "kind": "subscript_load",
    "code_line": 8,
    "expression": "n['runs']",
    "enclosing_scopes": [
      "If",
      "For"
    ]
  },
  {
    "field": "runs",
    "kind": "subscript_load",
    "code_line": 4,
    "expression": "n['runs']",
    "enclosing_scopes": [
      "comprehension",
      "If",
      "For"
    ]
  },
  {
    "field": "runs",
    "kind": "subscript_load",
    "code_line": 4,
    "expression": "n['runs']",
    "enclosing_scopes": [
      "comprehension",
      "If",
      "For"
    ]
  },
  {
    "field": "runs",
    "kind": "subscript_load",
    "code_line": 5,
    "expression": "n['runs']",
    "enclosing_scopes": [
      "If",
      "For"
    ]
  },
  {
    "field": "runs",
    "kind": "subscript_load",
    "code_line": 5,
    "expression": "n['runs']",
    "enclosing_scopes": [
      "If",
      "For"
    ]
  }
]
```

## ar25-0c556536 · segmentation_runs · call_b98322a27c9d40d18031ca4a

原件：runs/031-natural-aligned/segmentation_runs/ar25-0c556536_p0_requests.jsonl:55；analysis_step=18，snapshot_action=42。

```json
[
  {
    "field": "runs",
    "kind": "subscript_load",
    "code_line": 7,
    "expression": "n['runs']",
    "enclosing_scopes": []
  },
  {
    "field": "runs",
    "kind": "subscript_load",
    "code_line": 7,
    "expression": "n['runs']",
    "enclosing_scopes": [
      "comprehension"
    ]
  }
]
```

## ar25-0c556536 · segmentation_runs · call_c83f7645cb784f299001fb3d

原件：runs/031-natural-aligned/segmentation_runs/ar25-0c556536_p0_requests.jsonl:59；analysis_step=20，snapshot_action=51。

```json
[
  {
    "field": "runs",
    "kind": "subscript_load",
    "code_line": 4,
    "expression": "n['runs']",
    "enclosing_scopes": [
      "If",
      "For",
      "FunctionDef"
    ]
  },
  {
    "field": "runs",
    "kind": "subscript_load",
    "code_line": 4,
    "expression": "n['runs']",
    "enclosing_scopes": [
      "comprehension",
      "If",
      "For",
      "FunctionDef"
    ]
  }
]
```

## ar25-0c556536 · segmentation_runs · call_14fba814a88a43ef9204e1e7

原件：runs/031-natural-aligned/segmentation_runs/ar25-0c556536_p0_requests.jsonl:61；analysis_step=21，snapshot_action=57。

```json
[
  {
    "field": "runs",
    "kind": "subscript_load",
    "code_line": 9,
    "expression": "n['runs']",
    "enclosing_scopes": []
  },
  {
    "field": "runs",
    "kind": "subscript_load",
    "code_line": 9,
    "expression": "n['runs']",
    "enclosing_scopes": [
      "comprehension"
    ]
  }
]
```

## ar25-0c556536 · segmentation_runs · call_10428c285a244b01921cd91a

原件：runs/031-natural-aligned/segmentation_runs/ar25-0c556536_p0_requests.jsonl:63；analysis_step=22，snapshot_action=58。

```json
[
  {
    "field": "runs",
    "kind": "subscript_load",
    "code_line": 5,
    "expression": "n['runs']",
    "enclosing_scopes": [
      "If",
      "For",
      "FunctionDef"
    ]
  },
  {
    "field": "runs",
    "kind": "subscript_load",
    "code_line": 10,
    "expression": "n['runs']",
    "enclosing_scopes": [
      "If",
      "For",
      "FunctionDef"
    ]
  },
  {
    "field": "runs",
    "kind": "subscript_load",
    "code_line": 10,
    "expression": "n['runs']",
    "enclosing_scopes": [
      "If",
      "For",
      "FunctionDef"
    ]
  },
  {
    "field": "runs",
    "kind": "subscript_load",
    "code_line": 5,
    "expression": "n['runs']",
    "enclosing_scopes": [
      "comprehension",
      "If",
      "For",
      "FunctionDef"
    ]
  }
]
```

## ar25-0c556536 · segmentation_runs · call_f72d3e39f2ac4502b1fe9da3

原件：runs/031-natural-aligned/segmentation_runs/ar25-0c556536_p0_requests.jsonl:65；analysis_step=23，snapshot_action=75。

```json
[
  {
    "field": "runs",
    "kind": "subscript_load",
    "code_line": 4,
    "expression": "n['runs']",
    "enclosing_scopes": [
      "If",
      "For",
      "FunctionDef"
    ]
  },
  {
    "field": "runs",
    "kind": "subscript_load",
    "code_line": 4,
    "expression": "n['runs']",
    "enclosing_scopes": [
      "comprehension",
      "If",
      "For",
      "FunctionDef"
    ]
  }
]
```

## ar25-0c556536 · segmentation_runs · call_1725ea8e350f4c6c85e6d20c

原件：runs/031-natural-aligned/segmentation_runs/ar25-0c556536_p0_requests.jsonl:67；analysis_step=23，snapshot_action=75。

```json
[
  {
    "field": "runs",
    "kind": "subscript_load",
    "code_line": 4,
    "expression": "n['runs']",
    "enclosing_scopes": [
      "comprehension",
      "For"
    ]
  },
  {
    "field": "runs",
    "kind": "subscript_load",
    "code_line": 4,
    "expression": "n['runs']",
    "enclosing_scopes": [
      "comprehension",
      "For"
    ]
  },
  {
    "field": "runs",
    "kind": "subscript_load",
    "code_line": 5,
    "expression": "n['runs']",
    "enclosing_scopes": [
      "For"
    ]
  },
  {
    "field": "runs",
    "kind": "subscript_load",
    "code_line": 5,
    "expression": "n['runs']",
    "enclosing_scopes": [
      "For"
    ]
  }
]
```

## ar25-0c556536 · segmentation_runs · call_e4fcdbd17ec04421812e1c3d

原件：runs/031-natural-aligned/segmentation_runs/ar25-0c556536_p0_requests.jsonl:73；analysis_step=26，snapshot_action=78。

```json
[
  {
    "field": "runs",
    "kind": "subscript_load",
    "code_line": 7,
    "expression": "n['runs']",
    "enclosing_scopes": []
  },
  {
    "field": "runs",
    "kind": "subscript_load",
    "code_line": 8,
    "expression": "n['runs']",
    "enclosing_scopes": []
  },
  {
    "field": "runs",
    "kind": "subscript_load",
    "code_line": 7,
    "expression": "n['runs']",
    "enclosing_scopes": [
      "comprehension"
    ]
  },
  {
    "field": "runs",
    "kind": "subscript_load",
    "code_line": 7,
    "expression": "n['runs']",
    "enclosing_scopes": [
      "comprehension"
    ]
  },
  {
    "field": "runs",
    "kind": "subscript_load",
    "code_line": 8,
    "expression": "n['runs']",
    "enclosing_scopes": [
      "comprehension"
    ]
  }
]
```

## ar25-0c556536 · segmentation_runs · call_828ff89e07e24ee29749ff39

原件：runs/031-natural-aligned/segmentation_runs/ar25-0c556536_p0_requests.jsonl:75；analysis_step=27，snapshot_action=84。

```json
[
  {
    "field": "runs",
    "kind": "subscript_load",
    "code_line": 5,
    "expression": "n['runs']",
    "enclosing_scopes": [
      "For",
      "Try"
    ]
  },
  {
    "field": "runs",
    "kind": "subscript_load",
    "code_line": 5,
    "expression": "n['runs']",
    "enclosing_scopes": [
      "For",
      "Try"
    ]
  }
]
```

## ar25-0c556536 · segmentation_runs · call_ce5acabbccc9431cadf61e4d

原件：runs/031-natural-aligned/segmentation_runs/ar25-0c556536_p0_requests.jsonl:77；analysis_step=27，snapshot_action=84。

```json
[
  {
    "field": "runs",
    "kind": "subscript_load",
    "code_line": 6,
    "expression": "n['runs']",
    "enclosing_scopes": []
  },
  {
    "field": "runs",
    "kind": "subscript_load",
    "code_line": 6,
    "expression": "n['runs']",
    "enclosing_scopes": []
  },
  {
    "field": "runs",
    "kind": "subscript_load",
    "code_line": 4,
    "expression": "n['runs']",
    "enclosing_scopes": [
      "comprehension",
      "If",
      "For"
    ]
  },
  {
    "field": "runs",
    "kind": "subscript_load",
    "code_line": 4,
    "expression": "n['runs']",
    "enclosing_scopes": [
      "comprehension",
      "If",
      "For"
    ]
  },
  {
    "field": "runs",
    "kind": "subscript_load",
    "code_line": 5,
    "expression": "n['runs']",
    "enclosing_scopes": [
      "If",
      "For"
    ]
  },
  {
    "field": "runs",
    "kind": "subscript_load",
    "code_line": 5,
    "expression": "n['runs']",
    "enclosing_scopes": [
      "If",
      "For"
    ]
  }
]
```

## ar25-0c556536 · segmentation_runs · call_b91cf51cea2c4a5a8b6aa866

原件：runs/031-natural-aligned/segmentation_runs/ar25-0c556536_p0_requests.jsonl:81；analysis_step=28，snapshot_action=90。

```json
[
  {
    "field": "runs",
    "kind": "subscript_load",
    "code_line": 2,
    "expression": "n['runs']",
    "enclosing_scopes": [
      "FunctionDef"
    ]
  },
  {
    "field": "runs",
    "kind": "subscript_load",
    "code_line": 2,
    "expression": "n['runs']",
    "enclosing_scopes": [
      "FunctionDef"
    ]
  }
]
```

## ar25-0c556536 · segmentation_runs · call_a674c00e7a654bfbb1bae9b1

原件：runs/031-natural-aligned/segmentation_runs/ar25-0c556536_p0_requests.jsonl:85；analysis_step=30，snapshot_action=98。

```json
[
  {
    "field": "runs",
    "kind": "subscript_load",
    "code_line": 4,
    "expression": "n['runs']",
    "enclosing_scopes": [
      "If",
      "For",
      "FunctionDef"
    ]
  },
  {
    "field": "runs",
    "kind": "subscript_load",
    "code_line": 4,
    "expression": "n['runs']",
    "enclosing_scopes": [
      "comprehension",
      "If",
      "For",
      "FunctionDef"
    ]
  }
]
```

## ar25-0c556536 · segmentation_runs · call_62ffd011b2fb47879b111541

原件：runs/031-natural-aligned/segmentation_runs/ar25-0c556536_p0_requests.jsonl:89；analysis_step=32，snapshot_action=106。

```json
[
  {
    "field": "runs",
    "kind": "subscript_load",
    "code_line": 4,
    "expression": "n['runs']",
    "enclosing_scopes": [
      "If",
      "For",
      "FunctionDef"
    ]
  },
  {
    "field": "runs",
    "kind": "subscript_load",
    "code_line": 4,
    "expression": "n['runs']",
    "enclosing_scopes": [
      "comprehension",
      "If",
      "For",
      "FunctionDef"
    ]
  }
]
```

## ar25-0c556536 · segmentation_runs · call_82a55d9da3bf4b4b9ff50846

原件：runs/031-natural-aligned/segmentation_runs/ar25-0c556536_p0_requests.jsonl:91；analysis_step=32，snapshot_action=106。

```json
[
  {
    "field": "runs",
    "kind": "subscript_load",
    "code_line": 6,
    "expression": "n['runs']",
    "enclosing_scopes": []
  },
  {
    "field": "runs",
    "kind": "subscript_load",
    "code_line": 6,
    "expression": "n['runs']",
    "enclosing_scopes": []
  },
  {
    "field": "runs",
    "kind": "subscript_load",
    "code_line": 4,
    "expression": "n['runs']",
    "enclosing_scopes": [
      "comprehension",
      "If",
      "For"
    ]
  },
  {
    "field": "runs",
    "kind": "subscript_load",
    "code_line": 4,
    "expression": "n['runs']",
    "enclosing_scopes": [
      "comprehension",
      "If",
      "For"
    ]
  },
  {
    "field": "runs",
    "kind": "subscript_load",
    "code_line": 5,
    "expression": "n['runs']",
    "enclosing_scopes": [
      "If",
      "For"
    ]
  },
  {
    "field": "runs",
    "kind": "subscript_load",
    "code_line": 5,
    "expression": "n['runs']",
    "enclosing_scopes": [
      "If",
      "For"
    ]
  }
]
```

## m0r0-492f87ba · segmentation_runs · call_c444cb85b20e4cc5b2bd3d74

原件：runs/031-natural-aligned/segmentation_runs/m0r0-492f87ba_p0_requests.jsonl:3；analysis_step=1，snapshot_action=1。

```json
[
  {
    "field": "runs",
    "kind": "subscript_load",
    "code_line": 5,
    "expression": "n['runs']",
    "enclosing_scopes": [
      "For"
    ]
  }
]
```

## m0r0-492f87ba · segmentation_runs · call_1d571657b6664ebc822c9de8

原件：runs/031-natural-aligned/segmentation_runs/m0r0-492f87ba_p0_requests.jsonl:5；analysis_step=1，snapshot_action=1。

```json
[
  {
    "field": "runs",
    "kind": "subscript_load",
    "code_line": 3,
    "expression": "n3['runs']",
    "enclosing_scopes": [
      "For"
    ]
  }
]
```

## m0r0-492f87ba · segmentation_runs · call_d89e7aa00231492b9bff762e

原件：runs/031-natural-aligned/segmentation_runs/m0r0-492f87ba_p0_requests.jsonl:9；analysis_step=2，snapshot_action=2。

```json
[
  {
    "field": "runs",
    "kind": "subscript_load",
    "code_line": 6,
    "expression": "n['runs']",
    "enclosing_scopes": [
      "For",
      "For",
      "FunctionDef"
    ]
  }
]
```

## m0r0-492f87ba · segmentation_runs · call_2f929a5b4c2345319d6a3778

原件：runs/031-natural-aligned/segmentation_runs/m0r0-492f87ba_p0_requests.jsonl:33；analysis_step=6，snapshot_action=6。

```json
[
  {
    "field": "runs",
    "kind": "subscript_load",
    "code_line": 5,
    "expression": "n['runs']",
    "enclosing_scopes": [
      "For",
      "If",
      "For",
      "FunctionDef"
    ]
  }
]
```

## m0r0-492f87ba · segmentation_runs · call_0cd0f354a1424ae0a19859af

原件：runs/031-natural-aligned/segmentation_runs/m0r0-492f87ba_p0_requests.jsonl:47；analysis_step=7，snapshot_action=7。

```json
[
  {
    "field": "runs",
    "kind": "subscript_load",
    "code_line": 6,
    "expression": "n['runs']",
    "enclosing_scopes": [
      "For",
      "For",
      "FunctionDef"
    ]
  }
]
```

## tr87-cd924810 · segmentation_runs · call_422cc90409c24d35a88f4530

原件：runs/031-natural-aligned/segmentation_runs/tr87-cd924810_p0_requests.jsonl:3；analysis_step=1，snapshot_action=1。

```json
[
  {
    "field": "runs",
    "kind": "subscript_load",
    "code_line": 5,
    "expression": "n['runs']",
    "enclosing_scopes": [
      "For"
    ]
  },
  {
    "field": "boundary",
    "kind": "subscript_load",
    "code_line": 5,
    "expression": "n['boundary']",
    "enclosing_scopes": [
      "For"
    ]
  }
]
```

## tr87-cd924810 · segmentation_runs · call_796d278b4cd74b1183a77c7e

原件：runs/031-natural-aligned/segmentation_runs/tr87-cd924810_p0_requests.jsonl:9；analysis_step=3，snapshot_action=6。

```json
[
  {
    "field": "runs",
    "kind": "subscript_load",
    "code_line": 6,
    "expression": "n['runs']",
    "enclosing_scopes": [
      "For",
      "FunctionDef"
    ]
  }
]
```

## tr87-cd924810 · segmentation_runs · call_051fd58e251241cfb9b4648d

原件：runs/031-natural-aligned/segmentation_runs/tr87-cd924810_p0_requests.jsonl:15；analysis_step=5，snapshot_action=8。

```json
[
  {
    "field": "runs",
    "kind": "subscript_load",
    "code_line": 15,
    "expression": "n['runs']",
    "enclosing_scopes": [
      "FunctionDef"
    ]
  }
]
```

## tr87-cd924810 · segmentation_runs · call_74ca916e411747e4b43ca426

原件：runs/031-natural-aligned/segmentation_runs/tr87-cd924810_p0_requests.jsonl:29；analysis_step=7，snapshot_action=32。

```json
[
  {
    "field": "runs",
    "kind": "subscript_load",
    "code_line": 3,
    "expression": "n['runs']",
    "enclosing_scopes": [
      "For"
    ]
  },
  {
    "field": "runs",
    "kind": "subscript_load",
    "code_line": 3,
    "expression": "n['runs']",
    "enclosing_scopes": [
      "For"
    ]
  }
]
```

## tr87-cd924810 · segmentation_runs · call_334fe460ab3a411fa1f65fc6

原件：runs/031-natural-aligned/segmentation_runs/tr87-cd924810_p0_requests.jsonl:31；analysis_step=7，snapshot_action=32。

```json
[
  {
    "field": "runs",
    "kind": "subscript_load",
    "code_line": 5,
    "expression": "n['runs']",
    "enclosing_scopes": [
      "For",
      "For",
      "FunctionDef"
    ]
  },
  {
    "field": "runs",
    "kind": "subscript_load",
    "code_line": 36,
    "expression": "p['runs']",
    "enclosing_scopes": [
      "While",
      "For"
    ]
  },
  {
    "field": "runs",
    "kind": "subscript_load",
    "code_line": 36,
    "expression": "p['runs']",
    "enclosing_scopes": [
      "While",
      "For"
    ]
  },
  {
    "field": "runs",
    "kind": "subscript_load",
    "code_line": 37,
    "expression": "y['runs']",
    "enclosing_scopes": [
      "While",
      "For"
    ]
  },
  {
    "field": "runs",
    "kind": "subscript_load",
    "code_line": 37,
    "expression": "y['runs']",
    "enclosing_scopes": [
      "While",
      "For"
    ]
  },
  {
    "field": "runs",
    "kind": "subscript_load",
    "code_line": 32,
    "expression": "n['runs']",
    "enclosing_scopes": [
      "Lambda",
      "For"
    ]
  },
  {
    "field": "runs",
    "kind": "subscript_load",
    "code_line": 31,
    "expression": "n['runs']",
    "enclosing_scopes": [
      "comprehension",
      "For"
    ]
  },
  {
    "field": "runs",
    "kind": "subscript_load",
    "code_line": 38,
    "expression": "p['runs']",
    "enclosing_scopes": [
      "While",
      "For"
    ]
  }
]
```

## tr87-cd924810 · segmentation_runs · call_05be22be63884943aa5e344d

原件：runs/031-natural-aligned/segmentation_runs/tr87-cd924810_p0_requests.jsonl:33；analysis_step=7，snapshot_action=32。

```json
[
  {
    "field": "runs",
    "kind": "subscript_load",
    "code_line": 21,
    "expression": "p['runs']",
    "enclosing_scopes": [
      "For",
      "For"
    ]
  },
  {
    "field": "runs",
    "kind": "subscript_load",
    "code_line": 23,
    "expression": "y['runs']",
    "enclosing_scopes": [
      "For",
      "For"
    ]
  },
  {
    "field": "runs",
    "kind": "subscript_load",
    "code_line": 13,
    "expression": "n['runs']",
    "enclosing_scopes": [
      "comprehension",
      "FunctionDef"
    ]
  },
  {
    "field": "runs",
    "kind": "subscript_load",
    "code_line": 14,
    "expression": "n['runs']",
    "enclosing_scopes": [
      "Lambda",
      "FunctionDef"
    ]
  },
  {
    "field": "runs",
    "kind": "subscript_load",
    "code_line": 21,
    "expression": "p['runs']",
    "enclosing_scopes": [
      "For",
      "For"
    ]
  },
  {
    "field": "runs",
    "kind": "subscript_load",
    "code_line": 21,
    "expression": "p['runs']",
    "enclosing_scopes": [
      "For",
      "For"
    ]
  },
  {
    "field": "runs",
    "kind": "subscript_load",
    "code_line": 23,
    "expression": "y['runs']",
    "enclosing_scopes": [
      "For",
      "For"
    ]
  },
  {
    "field": "runs",
    "kind": "subscript_load",
    "code_line": 23,
    "expression": "y['runs']",
    "enclosing_scopes": [
      "For",
      "For"
    ]
  },
  {
    "field": "runs",
    "kind": "subscript_load",
    "code_line": 24,
    "expression": "p['runs']",
    "enclosing_scopes": [
      "For",
      "For"
    ]
  },
  {
    "field": "runs",
    "kind": "subscript_load",
    "code_line": 22,
    "expression": "y['runs']",
    "enclosing_scopes": [
      "For",
      "For"
    ]
  },
  {
    "field": "runs",
    "kind": "subscript_load",
    "code_line": 22,
    "expression": "y['runs']",
    "enclosing_scopes": [
      "For",
      "For"
    ]
  }
]
```

## tr87-cd924810 · segmentation_runs · call_38cd986a49924b3cb135da80

原件：runs/031-natural-aligned/segmentation_runs/tr87-cd924810_p0_requests.jsonl:35；analysis_step=7，snapshot_action=32。

```json
[
  {
    "field": "runs",
    "kind": "subscript_load",
    "code_line": 2,
    "expression": "n['runs']",
    "enclosing_scopes": [
      "comprehension",
      "FunctionDef"
    ]
  },
  {
    "field": "runs",
    "kind": "subscript_load",
    "code_line": 2,
    "expression": "n['runs']",
    "enclosing_scopes": [
      "comprehension",
      "FunctionDef"
    ]
  }
]
```

## tr87-cd924810 · segmentation_runs · call_117c7702d9054881b8451eb1

原件：runs/031-natural-aligned/segmentation_runs/tr87-cd924810_p0_requests.jsonl:53；analysis_step=11，snapshot_action=69。

```json
[
  {
    "field": "runs",
    "kind": "subscript_load",
    "code_line": 4,
    "expression": "n['runs']",
    "enclosing_scopes": [
      "If",
      "For"
    ]
  },
  {
    "field": "runs",
    "kind": "subscript_load",
    "code_line": 4,
    "expression": "n['runs']",
    "enclosing_scopes": [
      "If",
      "For"
    ]
  }
]
```

## tr87-cd924810 · segmentation_runs · call_f13d7b03e347435f8a8fce76

原件：runs/031-natural-aligned/segmentation_runs/tr87-cd924810_p0_requests.jsonl:59；analysis_step=11，snapshot_action=69。

```json
[
  {
    "field": "runs",
    "kind": "subscript_load",
    "code_line": 4,
    "expression": "n['runs']",
    "enclosing_scopes": [
      "comprehension",
      "FunctionDef"
    ]
  },
  {
    "field": "runs",
    "kind": "subscript_load",
    "code_line": 5,
    "expression": "n['runs']",
    "enclosing_scopes": [
      "Lambda",
      "FunctionDef"
    ]
  }
]
```

## tr87-cd924810 · segmentation_runs · call_c6fa542ef7a14196a7703c20

原件：runs/031-natural-aligned/segmentation_runs/tr87-cd924810_p0_requests.jsonl:69；analysis_step=14，snapshot_action=97。

```json
[
  {
    "field": "runs",
    "kind": "subscript_load",
    "code_line": 4,
    "expression": "n['runs']",
    "enclosing_scopes": [
      "If",
      "For"
    ]
  },
  {
    "field": "runs",
    "kind": "subscript_load",
    "code_line": 4,
    "expression": "n['runs']",
    "enclosing_scopes": [
      "If",
      "For"
    ]
  }
]
```

## tr87-cd924810 · segmentation_runs · call_dada33329039431ab859428a

原件：runs/031-natural-aligned/segmentation_runs/tr87-cd924810_p0_requests.jsonl:89；analysis_step=17，snapshot_action=133。

```json
[
  {
    "field": "runs",
    "kind": "subscript_load",
    "code_line": 4,
    "expression": "n['runs']",
    "enclosing_scopes": [
      "If",
      "For"
    ]
  },
  {
    "field": "runs",
    "kind": "subscript_load",
    "code_line": 4,
    "expression": "n['runs']",
    "enclosing_scopes": [
      "If",
      "For"
    ]
  }
]
```

## ft09-0d8bbf25 · baseline · call_7c5d1d665ba247e78c1ff282

原件：runs/031-natural-aligned/baseline/ft09-0d8bbf25_p0_requests.jsonl:3；analysis_step=1，snapshot_action=1。

```json
[
  {
    "field": "boundary",
    "kind": "subscript_load",
    "code_line": 6,
    "expression": "n['boundary']",
    "enclosing_scopes": [
      "For"
    ]
  }
]
```

## ft09-0d8bbf25 · baseline · call_756bad72bad34e64a036ee2d

原件：runs/031-natural-aligned/baseline/ft09-0d8bbf25_p0_requests.jsonl:11；analysis_step=3，snapshot_action=5。

```json
[
  {
    "field": "boundary",
    "kind": "subscript_load",
    "code_line": 5,
    "expression": "n['boundary']",
    "enclosing_scopes": [
      "For"
    ]
  },
  {
    "field": "boundary",
    "kind": "subscript_load",
    "code_line": 5,
    "expression": "n['boundary']",
    "enclosing_scopes": [
      "For"
    ]
  }
]
```

## cd82-fb555c5d · baseline · call_1aaff7811fd241c4b8858ffe

原件：runs/031-natural-aligned/baseline/cd82-fb555c5d_p0_requests.jsonl:3；analysis_step=1，snapshot_action=1。

```json
[
  {
    "field": "boundary",
    "kind": "subscript_load",
    "code_line": 5,
    "expression": "n['boundary']",
    "enclosing_scopes": [
      "For"
    ]
  }
]
```

## cd82-fb555c5d · baseline · call_fcaa000a1112496ea3895f22

原件：runs/031-natural-aligned/baseline/cd82-fb555c5d_p0_requests.jsonl:7；analysis_step=2，snapshot_action=2。

```json
[
  {
    "field": "boundary",
    "kind": "subscript_load",
    "code_line": 7,
    "expression": "n['boundary']",
    "enclosing_scopes": [
      "For"
    ]
  }
]
```

## cd82-fb555c5d · baseline · call_b57d7b9223e24e3a866142f1

原件：runs/031-natural-aligned/baseline/cd82-fb555c5d_p0_requests.jsonl:9；analysis_step=2，snapshot_action=2。

```json
[
  {
    "field": "boundary",
    "kind": "subscript_load",
    "code_line": 3,
    "expression": "n['boundary']",
    "enclosing_scopes": [
      "For"
    ]
  }
]
```

## cd82-fb555c5d · baseline · call_0fbc1b1f9fc14cf6bd7db5fa

原件：runs/031-natural-aligned/baseline/cd82-fb555c5d_p0_requests.jsonl:27；analysis_step=9，snapshot_action=13。

```json
[
  {
    "field": "boundary",
    "kind": "subscript_load",
    "code_line": 5,
    "expression": "n['boundary']",
    "enclosing_scopes": [
      "For",
      "FunctionDef"
    ]
  }
]
```

## cd82-fb555c5d · baseline · call_004551ec7943417b8ad69468

原件：runs/031-natural-aligned/baseline/cd82-fb555c5d_p0_requests.jsonl:33；analysis_step=10，snapshot_action=15。

```json
[
  {
    "field": "boundary",
    "kind": "subscript_load",
    "code_line": 4,
    "expression": "n['boundary']",
    "enclosing_scopes": [
      "comprehension",
      "For"
    ]
  },
  {
    "field": "boundary",
    "kind": "subscript_load",
    "code_line": 4,
    "expression": "n['boundary']",
    "enclosing_scopes": [
      "comprehension",
      "For"
    ]
  },
  {
    "field": "boundary",
    "kind": "subscript_load",
    "code_line": 4,
    "expression": "n['boundary']",
    "enclosing_scopes": [
      "comprehension",
      "For"
    ]
  },
  {
    "field": "boundary",
    "kind": "subscript_load",
    "code_line": 4,
    "expression": "n['boundary']",
    "enclosing_scopes": [
      "comprehension",
      "For"
    ]
  }
]
```

## cd82-fb555c5d · baseline · call_f51268db453d45d2988a7dad

原件：runs/031-natural-aligned/baseline/cd82-fb555c5d_p0_requests.jsonl:49；analysis_step=12，snapshot_action=19。

```json
[
  {
    "field": "boundary",
    "kind": "subscript_load",
    "code_line": 4,
    "expression": "n['boundary']",
    "enclosing_scopes": [
      "For"
    ]
  }
]
```

## cd82-fb555c5d · baseline · call_4a4758d6f9ee4fdaa7ee2ad9

原件：runs/031-natural-aligned/baseline/cd82-fb555c5d_p0_requests.jsonl:57；analysis_step=15，snapshot_action=25。

```json
[
  {
    "field": "boundary",
    "kind": "subscript_load",
    "code_line": 3,
    "expression": "n['boundary']",
    "enclosing_scopes": [
      "For"
    ]
  }
]
```

## cd82-fb555c5d · baseline · call_2608b16bb4324cab997d4836

原件：runs/031-natural-aligned/baseline/cd82-fb555c5d_p0_requests.jsonl:63；analysis_step=16，snapshot_action=26。

```json
[
  {
    "field": "boundary",
    "kind": "subscript_load",
    "code_line": 5,
    "expression": "n['boundary']",
    "enclosing_scopes": [
      "For"
    ]
  }
]
```

## cd82-fb555c5d · baseline · call_78ab833a8a794c2ca626d628

原件：runs/031-natural-aligned/baseline/cd82-fb555c5d_p0_requests.jsonl:65；analysis_step=17，snapshot_action=27。

```json
[
  {
    "field": "boundary",
    "kind": "subscript_load",
    "code_line": 5,
    "expression": "n['boundary']",
    "enclosing_scopes": [
      "For"
    ]
  }
]
```

## cd82-fb555c5d · baseline · call_0d1573e29c9f4100bb09a20d

原件：runs/031-natural-aligned/baseline/cd82-fb555c5d_p0_requests.jsonl:69；analysis_step=17，snapshot_action=27。

```json
[
  {
    "field": "boundary",
    "kind": "subscript_load",
    "code_line": 2,
    "expression": "n['boundary']",
    "enclosing_scopes": [
      "For"
    ]
  }
]
```

## re86-8af5384d · baseline · call_7e4ee08bf269479c8395b28f

原件：runs/031-natural-aligned/baseline/re86-8af5384d_p0_requests.jsonl:3；analysis_step=1，snapshot_action=1。

```json
[
  {
    "field": "boundary",
    "kind": "subscript_load",
    "code_line": 7,
    "expression": "n['boundary']",
    "enclosing_scopes": [
      "For"
    ]
  }
]
```

## re86-8af5384d · baseline · call_4ce52fafd37142dcb2e405c4

原件：runs/031-natural-aligned/baseline/re86-8af5384d_p0_requests.jsonl:21；analysis_step=6，snapshot_action=31。

```json
[
  {
    "field": "boundary",
    "kind": "subscript_load",
    "code_line": 3,
    "expression": "n['boundary']",
    "enclosing_scopes": [
      "For"
    ]
  },
  {
    "field": "boundary",
    "kind": "subscript_load",
    "code_line": 3,
    "expression": "n['boundary']",
    "enclosing_scopes": [
      "For"
    ]
  },
  {
    "field": "boundary",
    "kind": "subscript_load",
    "code_line": 3,
    "expression": "n['boundary']",
    "enclosing_scopes": [
      "For"
    ]
  }
]
```

## re86-8af5384d · baseline · call_45e388a8584541e78adafa49

原件：runs/031-natural-aligned/baseline/re86-8af5384d_p0_requests.jsonl:35；analysis_step=9，snapshot_action=70。

```json
[
  {
    "field": "boundary",
    "kind": "subscript_load",
    "code_line": 11,
    "expression": "n['boundary']",
    "enclosing_scopes": [
      "If",
      "For"
    ]
  }
]
```

## re86-8af5384d · baseline · call_356e841a58194c8f9c709b8a

原件：runs/031-natural-aligned/baseline/re86-8af5384d_p0_requests.jsonl:53；analysis_step=10，snapshot_action=117。

```json
[
  {
    "field": "boundary",
    "kind": "subscript_load",
    "code_line": 7,
    "expression": "n['boundary']",
    "enclosing_scopes": [
      "If",
      "For"
    ]
  },
  {
    "field": "boundary",
    "kind": "subscript_load",
    "code_line": 7,
    "expression": "n['boundary']",
    "enclosing_scopes": [
      "If",
      "For"
    ]
  }
]
```

## re86-8af5384d · baseline · call_a19ea62a15784748a1a4d692

原件：runs/031-natural-aligned/baseline/re86-8af5384d_p0_requests.jsonl:79；analysis_step=18，snapshot_action=227。

```json
[
  {
    "field": "boundary",
    "kind": "subscript_load",
    "code_line": 6,
    "expression": "n['boundary']",
    "enclosing_scopes": [
      "If",
      "For"
    ]
  },
  {
    "field": "boundary",
    "kind": "subscript_load",
    "code_line": 6,
    "expression": "n['boundary']",
    "enclosing_scopes": [
      "If",
      "For"
    ]
  }
]
```

## r11l-495a7899 · baseline · call_b1605124db3243fc82acbf49

原件：runs/031-natural-aligned/baseline/r11l-495a7899_p0_requests.jsonl:3；analysis_step=1，snapshot_action=1。

```json
[
  {
    "field": "boundary",
    "kind": "subscript_load",
    "code_line": 6,
    "expression": "n['boundary']",
    "enclosing_scopes": [
      "For"
    ]
  }
]
```

## r11l-495a7899 · baseline · call_c787e1d119454d0cb2436d08

原件：runs/031-natural-aligned/baseline/r11l-495a7899_p0_requests.jsonl:7；analysis_step=2，snapshot_action=2。

```json
[
  {
    "field": "boundary",
    "kind": "subscript_load",
    "code_line": 5,
    "expression": "n['boundary']",
    "enclosing_scopes": [
      "If",
      "For"
    ]
  }
]
```

## r11l-495a7899 · baseline · call_ebc5954a095e4f0f8160619e

原件：runs/031-natural-aligned/baseline/r11l-495a7899_p0_requests.jsonl:13；analysis_step=4，snapshot_action=4。

```json
[
  {
    "field": "boundary",
    "kind": "subscript_load",
    "code_line": 7,
    "expression": "n['boundary']",
    "enclosing_scopes": [
      "If",
      "For"
    ]
  }
]
```

## r11l-495a7899 · baseline · call_0810af7240c84695a77b61f6

原件：runs/031-natural-aligned/baseline/r11l-495a7899_p0_requests.jsonl:17；analysis_step=5，snapshot_action=5。

```json
[
  {
    "field": "boundary",
    "kind": "subscript_load",
    "code_line": 6,
    "expression": "n['boundary']",
    "enclosing_scopes": [
      "For"
    ]
  }
]
```

## r11l-495a7899 · baseline · call_85614ae532eb46c3bbbe3177

原件：runs/031-natural-aligned/baseline/r11l-495a7899_p0_requests.jsonl:19；analysis_step=5，snapshot_action=5。

```json
[
  {
    "field": "boundary",
    "kind": "subscript_load",
    "code_line": 9,
    "expression": "n['boundary']",
    "enclosing_scopes": [
      "If",
      "For"
    ]
  },
  {
    "field": "boundary",
    "kind": "subscript_load",
    "code_line": 15,
    "expression": "n['boundary']",
    "enclosing_scopes": [
      "If",
      "For",
      "If"
    ]
  }
]
```

## r11l-495a7899 · baseline · call_9a57626277a24e1c976aef9c

原件：runs/031-natural-aligned/baseline/r11l-495a7899_p0_requests.jsonl:21；analysis_step=5，snapshot_action=5。

```json
[
  {
    "field": "boundary",
    "kind": "subscript_load",
    "code_line": 4,
    "expression": "n['boundary']",
    "enclosing_scopes": [
      "If",
      "For"
    ]
  },
  {
    "field": "boundary",
    "kind": "subscript_load",
    "code_line": 4,
    "expression": "n['boundary']",
    "enclosing_scopes": [
      "If",
      "For"
    ]
  },
  {
    "field": "boundary",
    "kind": "subscript_load",
    "code_line": 4,
    "expression": "n['boundary']",
    "enclosing_scopes": [
      "If",
      "For"
    ]
  }
]
```

## r11l-495a7899 · baseline · call_05bf1bbebc2543c88e7fec6f

原件：runs/031-natural-aligned/baseline/r11l-495a7899_p0_requests.jsonl:23；analysis_step=5，snapshot_action=5。

```json
[
  {
    "field": "boundary",
    "kind": "subscript_load",
    "code_line": 5,
    "expression": "n['boundary']",
    "enclosing_scopes": [
      "If",
      "For"
    ]
  }
]
```

## r11l-495a7899 · baseline · call_c75511427428437a894f68ba

原件：runs/031-natural-aligned/baseline/r11l-495a7899_p0_requests.jsonl:25；analysis_step=5，snapshot_action=5。

```json
[
  {
    "field": "boundary",
    "kind": "subscript_load",
    "code_line": 2,
    "expression": "n['boundary']",
    "enclosing_scopes": [
      "For"
    ]
  }
]
```

## r11l-495a7899 · baseline · call_a58a4e7faed04399abafa020

原件：runs/031-natural-aligned/baseline/r11l-495a7899_p0_requests.jsonl:33；analysis_step=6，snapshot_action=6。

```json
[
  {
    "field": "boundary",
    "kind": "subscript_load",
    "code_line": 2,
    "expression": "n['boundary']",
    "enclosing_scopes": [
      "For"
    ]
  }
]
```

## r11l-495a7899 · baseline · call_168c58058f8e457b8b9f2611

原件：runs/031-natural-aligned/baseline/r11l-495a7899_p0_requests.jsonl:41；analysis_step=8，snapshot_action=8。

```json
[
  {
    "field": "boundary",
    "kind": "subscript_load",
    "code_line": 8,
    "expression": "n['boundary']",
    "enclosing_scopes": [
      "If",
      "For"
    ]
  }
]
```

## r11l-495a7899 · baseline · call_a2064a4f3d8843ba8d115028

原件：runs/031-natural-aligned/baseline/r11l-495a7899_p0_requests.jsonl:49；analysis_step=9，snapshot_action=9。

```json
[
  {
    "field": "boundary",
    "kind": "subscript_load",
    "code_line": 6,
    "expression": "n['boundary']",
    "enclosing_scopes": [
      "If",
      "For"
    ]
  }
]
```

## r11l-495a7899 · baseline · call_7d6e6b6d69cf48eeb67039a3

原件：runs/031-natural-aligned/baseline/r11l-495a7899_p0_requests.jsonl:51；analysis_step=9，snapshot_action=9。

```json
[
  {
    "field": "boundary",
    "kind": "subscript_load",
    "code_line": 6,
    "expression": "n['boundary']",
    "enclosing_scopes": []
  }
]
```

## sp80-589a99af · baseline · call_67865606e8984b1d8b796c88

原件：runs/031-natural-aligned/baseline/sp80-589a99af_p0_requests.jsonl:3；analysis_step=1，snapshot_action=1。

```json
[
  {
    "field": "boundary",
    "kind": "subscript_load",
    "code_line": 5,
    "expression": "n['boundary']",
    "enclosing_scopes": [
      "For"
    ]
  }
]
```

## sp80-589a99af · baseline · call_b88e3a34acce4e60ad0040a0

原件：runs/031-natural-aligned/baseline/sp80-589a99af_p0_requests.jsonl:15；analysis_step=5，snapshot_action=8。

```json
[
  {
    "field": "boundary",
    "kind": "subscript_load",
    "code_line": 4,
    "expression": "n['boundary']",
    "enclosing_scopes": []
  }
]
```

## sp80-589a99af · baseline · call_d159ca5c5f26488b83526be1

原件：runs/031-natural-aligned/baseline/sp80-589a99af_p0_requests.jsonl:21；analysis_step=6，snapshot_action=10。

```json
[
  {
    "field": "boundary",
    "kind": "subscript_load",
    "code_line": 3,
    "expression": "n['boundary']",
    "enclosing_scopes": []
  }
]
```

## sp80-589a99af · baseline · call_3c83179c97fe496eababcd35

原件：runs/031-natural-aligned/baseline/sp80-589a99af_p0_requests.jsonl:23；analysis_step=6，snapshot_action=10。

```json
[
  {
    "field": "boundary",
    "kind": "subscript_load",
    "code_line": 3,
    "expression": "n['boundary']",
    "enclosing_scopes": [
      "For"
    ]
  },
  {
    "field": "boundary",
    "kind": "subscript_load",
    "code_line": 3,
    "expression": "n['boundary']",
    "enclosing_scopes": [
      "For"
    ]
  }
]
```

## sp80-589a99af · baseline · call_b9757cdd648c46e48470dede

原件：runs/031-natural-aligned/baseline/sp80-589a99af_p0_requests.jsonl:27；analysis_step=8，snapshot_action=14。

```json
[
  {
    "field": "boundary",
    "kind": "subscript_load",
    "code_line": 3,
    "expression": "n['boundary']",
    "enclosing_scopes": []
  }
]
```

## sp80-589a99af · baseline · call_6bb8307919d64a63b98ec81b

原件：runs/031-natural-aligned/baseline/sp80-589a99af_p0_requests.jsonl:29；analysis_step=9，snapshot_action=17。

```json
[
  {
    "field": "boundary",
    "kind": "subscript_load",
    "code_line": 13,
    "expression": "n['boundary']",
    "enclosing_scopes": [
      "For"
    ]
  },
  {
    "field": "boundary",
    "kind": "subscript_load",
    "code_line": 13,
    "expression": "n['boundary']",
    "enclosing_scopes": [
      "For"
    ]
  }
]
```

## sp80-589a99af · baseline · call_2043f94acac5467b8cbe66d3

原件：runs/031-natural-aligned/baseline/sp80-589a99af_p0_requests.jsonl:33；analysis_step=10，snapshot_action=20。

```json
[
  {
    "field": "boundary",
    "kind": "subscript_load",
    "code_line": 4,
    "expression": "n['boundary']",
    "enclosing_scopes": [
      "If",
      "For"
    ]
  },
  {
    "field": "boundary",
    "kind": "subscript_load",
    "code_line": 4,
    "expression": "n['boundary']",
    "enclosing_scopes": [
      "If",
      "For"
    ]
  }
]
```

## sp80-589a99af · baseline · call_fdc3720d3c4642d0aff4c31e

原件：runs/031-natural-aligned/baseline/sp80-589a99af_p0_requests.jsonl:35；analysis_step=11，snapshot_action=30。

```json
[
  {
    "field": "boundary",
    "kind": "subscript_load",
    "code_line": 5,
    "expression": "n['boundary']",
    "enclosing_scopes": [
      "If",
      "For"
    ]
  },
  {
    "field": "boundary",
    "kind": "subscript_load",
    "code_line": 5,
    "expression": "n['boundary']",
    "enclosing_scopes": [
      "If",
      "For"
    ]
  }
]
```

## sp80-589a99af · baseline · call_b234d2c82cce45938cd2539f

原件：runs/031-natural-aligned/baseline/sp80-589a99af_p0_requests.jsonl:39；analysis_step=12，snapshot_action=31。

```json
[
  {
    "field": "boundary",
    "kind": "subscript_load",
    "code_line": 3,
    "expression": "n['boundary']",
    "enclosing_scopes": [
      "For"
    ]
  },
  {
    "field": "boundary",
    "kind": "subscript_load",
    "code_line": 3,
    "expression": "n['boundary']",
    "enclosing_scopes": [
      "For"
    ]
  },
  {
    "field": "boundary",
    "kind": "subscript_load",
    "code_line": 3,
    "expression": "n['boundary']",
    "enclosing_scopes": [
      "For"
    ]
  }
]
```

## sp80-589a99af · baseline · call_331cd36ecfc74ec78f5079a0

原件：runs/031-natural-aligned/baseline/sp80-589a99af_p0_requests.jsonl:43；analysis_step=13，snapshot_action=44。

```json
[
  {
    "field": "boundary",
    "kind": "subscript_load",
    "code_line": 9,
    "expression": "n['boundary']",
    "enclosing_scopes": [
      "If",
      "For"
    ]
  },
  {
    "field": "boundary",
    "kind": "subscript_load",
    "code_line": 9,
    "expression": "n['boundary']",
    "enclosing_scopes": [
      "If",
      "For"
    ]
  },
  {
    "field": "boundary",
    "kind": "subscript_load",
    "code_line": 9,
    "expression": "n['boundary']",
    "enclosing_scopes": [
      "If",
      "For"
    ]
  },
  {
    "field": "boundary",
    "kind": "subscript_load",
    "code_line": 9,
    "expression": "n['boundary']",
    "enclosing_scopes": [
      "If",
      "For"
    ]
  }
]
```

## sp80-589a99af · baseline · call_990ca4574d0845a3b0a3988b

原件：runs/031-natural-aligned/baseline/sp80-589a99af_p0_requests.jsonl:49；analysis_step=15，snapshot_action=46。

```json
[
  {
    "field": "boundary",
    "kind": "subscript_load",
    "code_line": 4,
    "expression": "n['boundary']",
    "enclosing_scopes": [
      "If",
      "For"
    ]
  },
  {
    "field": "boundary",
    "kind": "subscript_load",
    "code_line": 4,
    "expression": "n['boundary']",
    "enclosing_scopes": [
      "If",
      "For"
    ]
  },
  {
    "field": "boundary",
    "kind": "subscript_load",
    "code_line": 4,
    "expression": "n['boundary']",
    "enclosing_scopes": [
      "If",
      "For"
    ]
  },
  {
    "field": "boundary",
    "kind": "subscript_load",
    "code_line": 4,
    "expression": "n['boundary']",
    "enclosing_scopes": [
      "If",
      "For"
    ]
  }
]
```

## sp80-589a99af · baseline · call_6781bcce674b42178caf0d34

原件：runs/031-natural-aligned/baseline/sp80-589a99af_p0_requests.jsonl:51；analysis_step=16，snapshot_action=47。

```json
[
  {
    "field": "boundary",
    "kind": "subscript_load",
    "code_line": 4,
    "expression": "n['boundary']",
    "enclosing_scopes": [
      "If",
      "For"
    ]
  },
  {
    "field": "boundary",
    "kind": "subscript_load",
    "code_line": 4,
    "expression": "n['boundary']",
    "enclosing_scopes": [
      "If",
      "For"
    ]
  },
  {
    "field": "boundary",
    "kind": "subscript_load",
    "code_line": 4,
    "expression": "n['boundary']",
    "enclosing_scopes": [
      "If",
      "For"
    ]
  },
  {
    "field": "boundary",
    "kind": "subscript_load",
    "code_line": 4,
    "expression": "n['boundary']",
    "enclosing_scopes": [
      "If",
      "For"
    ]
  }
]
```

## tu93-0768757b · baseline · call_f2b8b92c5a824d68aae6fed6

原件：runs/031-natural-aligned/baseline/tu93-0768757b_p0_requests.jsonl:3；analysis_step=1，snapshot_action=1。

```json
[
  {
    "field": "boundary",
    "kind": "subscript_load",
    "code_line": 5,
    "expression": "n['boundary']",
    "enclosing_scopes": [
      "For"
    ]
  }
]
```

## tu93-0768757b · baseline · call_b6e4d9b60e0245268296e3a1

原件：runs/031-natural-aligned/baseline/tu93-0768757b_p0_requests.jsonl:5；analysis_step=1，snapshot_action=1。

```json
[
  {
    "field": "boundary",
    "kind": "subscript_load",
    "code_line": 4,
    "expression": "n['boundary']",
    "enclosing_scopes": [
      "For"
    ]
  }
]
```

## tu93-0768757b · baseline · call_d7712b4be82949c188d4c50a

原件：runs/031-natural-aligned/baseline/tu93-0768757b_p0_requests.jsonl:7；analysis_step=1，snapshot_action=1。

```json
[
  {
    "field": "boundary",
    "kind": "subscript_load",
    "code_line": 4,
    "expression": "n['boundary']",
    "enclosing_scopes": [
      "For"
    ]
  }
]
```

## tu93-0768757b · baseline · call_bdebe0e2cf624ffaa017eff8

原件：runs/031-natural-aligned/baseline/tu93-0768757b_p0_requests.jsonl:11；analysis_step=2，snapshot_action=2。

```json
[
  {
    "field": "boundary",
    "kind": "subscript_load",
    "code_line": 4,
    "expression": "n['boundary']",
    "enclosing_scopes": [
      "For",
      "FunctionDef"
    ]
  }
]
```

## tu93-0768757b · baseline · call_20b9bf5d52d243ca9d8e8a01

原件：runs/031-natural-aligned/baseline/tu93-0768757b_p0_requests.jsonl:25；analysis_step=4，snapshot_action=19。

```json
[
  {
    "field": "boundary",
    "kind": "subscript_load",
    "code_line": 11,
    "expression": "n['boundary']",
    "enclosing_scopes": [
      "For",
      "For"
    ]
  },
  {
    "field": "boundary",
    "kind": "subscript_load",
    "code_line": 14,
    "expression": "n['boundary']",
    "enclosing_scopes": [
      "If",
      "For"
    ]
  }
]
```

## sc25-635fd71a · baseline · call_bd6f4d6703ec4d5ebbdf202d

原件：runs/031-natural-aligned/baseline/sc25-635fd71a_p0_requests.jsonl:3；analysis_step=1，snapshot_action=1。

```json
[
  {
    "field": "boundary",
    "kind": "subscript_load",
    "code_line": 7,
    "expression": "n['boundary']",
    "enclosing_scopes": [
      "For"
    ]
  }
]
```

## sc25-635fd71a · baseline · call_ab367dbcfd9148be898e4528

原件：runs/031-natural-aligned/baseline/sc25-635fd71a_p0_requests.jsonl:27；analysis_step=8，snapshot_action=13。

```json
[
  {
    "field": "boundary",
    "kind": "subscript_load",
    "code_line": 4,
    "expression": "n['boundary']",
    "enclosing_scopes": [
      "If",
      "For"
    ]
  }
]
```

## sc25-635fd71a · baseline · call_78ab8084dc67493ca318b73a

原件：runs/031-natural-aligned/baseline/sc25-635fd71a_p0_requests.jsonl:55；analysis_step=19，snapshot_action=41。

```json
[
  {
    "field": "boundary",
    "kind": "subscript_load",
    "code_line": 4,
    "expression": "n['boundary']",
    "enclosing_scopes": [
      "If",
      "For"
    ]
  },
  {
    "field": "boundary",
    "kind": "subscript_load",
    "code_line": 4,
    "expression": "n['boundary']",
    "enclosing_scopes": [
      "If",
      "For"
    ]
  }
]
```

## sc25-635fd71a · baseline · call_54ad1c565cb74c9ba06d607f

原件：runs/031-natural-aligned/baseline/sc25-635fd71a_p0_requests.jsonl:63；analysis_step=22，snapshot_action=46。

```json
[
  {
    "field": "boundary",
    "kind": "subscript_load",
    "code_line": 4,
    "expression": "n['boundary']",
    "enclosing_scopes": [
      "If",
      "For"
    ]
  },
  {
    "field": "boundary",
    "kind": "subscript_load",
    "code_line": 4,
    "expression": "n['boundary']",
    "enclosing_scopes": [
      "If",
      "For"
    ]
  }
]
```

## sc25-635fd71a · baseline · call_7f33d7a0aa1e4f14be3d65b8

原件：runs/031-natural-aligned/baseline/sc25-635fd71a_p0_requests.jsonl:89；analysis_step=31，snapshot_action=79。

```json
[
  {
    "field": "boundary",
    "kind": "subscript_load",
    "code_line": 4,
    "expression": "n['boundary']",
    "enclosing_scopes": [
      "If",
      "For"
    ]
  },
  {
    "field": "boundary",
    "kind": "subscript_load",
    "code_line": 4,
    "expression": "n['boundary']",
    "enclosing_scopes": [
      "If",
      "For"
    ]
  }
]
```

## ar25-0c556536 · baseline · call_2f3ecaf0c38746b4932a44c2

原件：runs/031-natural-aligned/baseline/ar25-0c556536_p0_requests.jsonl:3；analysis_step=1，snapshot_action=2。

```json
[
  {
    "field": "boundary",
    "kind": "subscript_load",
    "code_line": 5,
    "expression": "n['boundary']",
    "enclosing_scopes": [
      "For"
    ]
  }
]
```

## ar25-0c556536 · baseline · call_1e015717834f491ca0c2fdd1

原件：runs/031-natural-aligned/baseline/ar25-0c556536_p0_requests.jsonl:11；analysis_step=4，snapshot_action=13。

```json
[
  {
    "field": "boundary",
    "kind": "subscript_load",
    "code_line": 10,
    "expression": "n['boundary']",
    "enclosing_scopes": [
      "If",
      "For"
    ]
  }
]
```

## ar25-0c556536 · baseline · call_87a712b92b574380b120451b

原件：runs/031-natural-aligned/baseline/ar25-0c556536_p0_requests.jsonl:13；analysis_step=5，snapshot_action=17。

```json
[
  {
    "field": "boundary",
    "kind": "subscript_load",
    "code_line": 10,
    "expression": "n['boundary']",
    "enclosing_scopes": [
      "If",
      "For"
    ]
  }
]
```

## ar25-0c556536 · baseline · call_f21dc5eb68e34ec5aed7b03d

原件：runs/031-natural-aligned/baseline/ar25-0c556536_p0_requests.jsonl:15；analysis_step=5，snapshot_action=17。

```json
[
  {
    "field": "boundary",
    "kind": "subscript_load",
    "code_line": 3,
    "expression": "n['boundary']",
    "enclosing_scopes": [
      "For"
    ]
  }
]
```

## ar25-0c556536 · baseline · call_06414356d12e420c88968a3e

原件：runs/031-natural-aligned/baseline/ar25-0c556536_p0_requests.jsonl:19；analysis_step=6，snapshot_action=20。

```json
[
  {
    "field": "boundary",
    "kind": "subscript_load",
    "code_line": 5,
    "expression": "n['boundary']",
    "enclosing_scopes": [
      "If",
      "For",
      "FunctionDef"
    ]
  }
]
```

## ar25-0c556536 · baseline · call_ead63f66f7674da6a0a0c2fd

原件：runs/031-natural-aligned/baseline/ar25-0c556536_p0_requests.jsonl:21；analysis_step=6，snapshot_action=20。

```json
[
  {
    "field": "boundary",
    "kind": "subscript_load",
    "code_line": 7,
    "expression": "n['boundary']",
    "enclosing_scopes": [
      "If",
      "For",
      "For"
    ]
  }
]
```

## ar25-0c556536 · baseline · call_2eeb3170c9884460b529cbb9

原件：runs/031-natural-aligned/baseline/ar25-0c556536_p0_requests.jsonl:29；analysis_step=9，snapshot_action=35。

```json
[
  {
    "field": "boundary",
    "kind": "subscript_load",
    "code_line": 4,
    "expression": "n['boundary']",
    "enclosing_scopes": [
      "If",
      "For"
    ]
  }
]
```

## ar25-0c556536 · baseline · call_fa272e4c553b441c9e77fd9d

原件：runs/031-natural-aligned/baseline/ar25-0c556536_p0_requests.jsonl:33；analysis_step=10，snapshot_action=36。

```json
[
  {
    "field": "boundary",
    "kind": "subscript_load",
    "code_line": 5,
    "expression": "n['boundary']",
    "enclosing_scopes": [
      "If",
      "For",
      "FunctionDef"
    ]
  }
]
```

## ar25-0c556536 · baseline · call_1d21c8fc5aff4d5db27822ba

原件：runs/031-natural-aligned/baseline/ar25-0c556536_p0_requests.jsonl:35；analysis_step=11，snapshot_action=37。

```json
[
  {
    "field": "boundary",
    "kind": "subscript_load",
    "code_line": 5,
    "expression": "n['boundary']",
    "enclosing_scopes": [
      "If",
      "For",
      "FunctionDef"
    ]
  }
]
```

## ar25-0c556536 · baseline · call_d674d365e5c743ea8b5c1ce1

原件：runs/031-natural-aligned/baseline/ar25-0c556536_p0_requests.jsonl:41；analysis_step=14，snapshot_action=60。

```json
[
  {
    "field": "boundary",
    "kind": "subscript_load",
    "code_line": 4,
    "expression": "n['boundary']",
    "enclosing_scopes": [
      "If",
      "For",
      "FunctionDef"
    ]
  },
  {
    "field": "boundary",
    "kind": "subscript_load",
    "code_line": 3,
    "expression": "n['boundary']",
    "enclosing_scopes": [
      "If",
      "For",
      "FunctionDef"
    ]
  }
]
```

## ar25-0c556536 · baseline · call_e77957ae0d70432aa8c4d992

原件：runs/031-natural-aligned/baseline/ar25-0c556536_p0_requests.jsonl:43；analysis_step=14，snapshot_action=60。

```json
[
  {
    "field": "boundary",
    "kind": "subscript_load",
    "code_line": 3,
    "expression": "n['boundary']",
    "enclosing_scopes": [
      "If",
      "For"
    ]
  }
]
```

## ar25-0c556536 · baseline · call_7c07ad38a0644ce8b335dc54

原件：runs/031-natural-aligned/baseline/ar25-0c556536_p0_requests.jsonl:45；analysis_step=15，snapshot_action=61。

```json
[
  {
    "field": "boundary",
    "kind": "subscript_load",
    "code_line": 5,
    "expression": "n['boundary']",
    "enclosing_scopes": [
      "If",
      "For",
      "FunctionDef"
    ]
  }
]
```

## ar25-0c556536 · baseline · call_5427a164833045d7bd9642f1

原件：runs/031-natural-aligned/baseline/ar25-0c556536_p0_requests.jsonl:47；analysis_step=16，snapshot_action=78。

```json
[
  {
    "field": "boundary",
    "kind": "subscript_load",
    "code_line": 4,
    "expression": "n['boundary']",
    "enclosing_scopes": [
      "If",
      "For",
      "FunctionDef"
    ]
  }
]
```

## ar25-0c556536 · baseline · call_cda26376fea34e23b3f744cd

原件：runs/031-natural-aligned/baseline/ar25-0c556536_p0_requests.jsonl:49；analysis_step=16，snapshot_action=78。

```json
[
  {
    "field": "boundary",
    "kind": "subscript_load",
    "code_line": 3,
    "expression": "n['boundary']",
    "enclosing_scopes": [
      "If",
      "For"
    ]
  }
]
```

## ar25-0c556536 · baseline · call_20a51d62100d4998a60ea5af

原件：runs/031-natural-aligned/baseline/ar25-0c556536_p0_requests.jsonl:51；analysis_step=16，snapshot_action=78。

```json
[
  {
    "field": "boundary",
    "kind": "subscript_load",
    "code_line": 11,
    "expression": "n['boundary']",
    "enclosing_scopes": [
      "If",
      "For"
    ]
  }
]
```

## ar25-0c556536 · baseline · call_c3aeb39f381148c48756764c

原件：runs/031-natural-aligned/baseline/ar25-0c556536_p0_requests.jsonl:53；analysis_step=17，snapshot_action=80。

```json
[
  {
    "field": "boundary",
    "kind": "subscript_load",
    "code_line": 2,
    "expression": "n['boundary']",
    "enclosing_scopes": [
      "FunctionDef"
    ]
  }
]
```

## ar25-0c556536 · baseline · call_6f1ce1f434764dd8b2830c3c

原件：runs/031-natural-aligned/baseline/ar25-0c556536_p0_requests.jsonl:57；analysis_step=18，snapshot_action=109。

```json
[
  {
    "field": "boundary",
    "kind": "subscript_load",
    "code_line": 3,
    "expression": "n['boundary']",
    "enclosing_scopes": [
      "If",
      "For"
    ]
  },
  {
    "field": "boundary",
    "kind": "subscript_load",
    "code_line": 7,
    "expression": "n['boundary']",
    "enclosing_scopes": [
      "If",
      "For"
    ]
  }
]
```

## ar25-0c556536 · baseline · call_f01dad635f694202a0ccb731

原件：runs/031-natural-aligned/baseline/ar25-0c556536_p0_requests.jsonl:59；analysis_step=18，snapshot_action=109。

```json
[
  {
    "field": "boundary",
    "kind": "subscript_load",
    "code_line": 2,
    "expression": "n['boundary']",
    "enclosing_scopes": [
      "For"
    ]
  },
  {
    "field": "boundary",
    "kind": "subscript_load",
    "code_line": 5,
    "expression": "n['boundary']",
    "enclosing_scopes": []
  },
  {
    "field": "boundary",
    "kind": "subscript_load",
    "code_line": 7,
    "expression": "n['boundary']",
    "enclosing_scopes": []
  }
]
```

## ar25-0c556536 · baseline · call_b6084f3408ed400485bc1f95

原件：runs/031-natural-aligned/baseline/ar25-0c556536_p0_requests.jsonl:73；analysis_step=19，snapshot_action=112。

```json
[
  {
    "field": "boundary",
    "kind": "subscript_load",
    "code_line": 2,
    "expression": "n['boundary']",
    "enclosing_scopes": [
      "FunctionDef"
    ]
  }
]
```

## m0r0-492f87ba · baseline · call_f3c0ff6993ae424596ccb7c9

原件：runs/031-natural-aligned/baseline/m0r0-492f87ba_p0_requests.jsonl:3；analysis_step=1，snapshot_action=1。

```json
[
  {
    "field": "boundary",
    "kind": "subscript_load",
    "code_line": 7,
    "expression": "n['boundary']",
    "enclosing_scopes": [
      "For"
    ]
  }
]
```

## m0r0-492f87ba · baseline · call_426afd24e9104b3ea46674fc

原件：runs/031-natural-aligned/baseline/m0r0-492f87ba_p0_requests.jsonl:27；analysis_step=4，snapshot_action=18。

```json
[
  {
    "field": "boundary",
    "kind": "subscript_load",
    "code_line": 10,
    "expression": "n['boundary']",
    "enclosing_scopes": [
      "If",
      "For",
      "FunctionDef"
    ]
  }
]
```

## m0r0-492f87ba · baseline · call_54c18cc1ccc9477aa9a78863

原件：runs/031-natural-aligned/baseline/m0r0-492f87ba_p0_requests.jsonl:31；analysis_step=6，snapshot_action=21。

```json
[
  {
    "field": "boundary",
    "kind": "subscript_load",
    "code_line": 4,
    "expression": "n['boundary']",
    "enclosing_scopes": [
      "If",
      "For"
    ]
  },
  {
    "field": "boundary",
    "kind": "subscript_load",
    "code_line": 9,
    "expression": "n['boundary']",
    "enclosing_scopes": [
      "If",
      "For"
    ]
  }
]
```

## m0r0-492f87ba · baseline · call_c8c20c1039024af9b92e8f77

原件：runs/031-natural-aligned/baseline/m0r0-492f87ba_p0_requests.jsonl:33；analysis_step=7，snapshot_action=22。

```json
[
  {
    "field": "boundary",
    "kind": "subscript_load",
    "code_line": 4,
    "expression": "n['boundary']",
    "enclosing_scopes": []
  }
]
```

## m0r0-492f87ba · baseline · call_178737b774974edcbab4d490

原件：runs/031-natural-aligned/baseline/m0r0-492f87ba_p0_requests.jsonl:37；analysis_step=8，snapshot_action=23。

```json
[
  {
    "field": "boundary",
    "kind": "subscript_load",
    "code_line": 4,
    "expression": "n['boundary']",
    "enclosing_scopes": []
  }
]
```

## m0r0-492f87ba · baseline · call_642023218662462e9ed600bb

原件：runs/031-natural-aligned/baseline/m0r0-492f87ba_p0_requests.jsonl:39；analysis_step=8，snapshot_action=23。

```json
[
  {
    "field": "boundary",
    "kind": "subscript_load",
    "code_line": 29,
    "expression": "n['boundary']",
    "enclosing_scopes": [
      "For"
    ]
  }
]
```

## m0r0-492f87ba · baseline · call_db57bcf2dd7f47ceacc1bd85

原件：runs/031-natural-aligned/baseline/m0r0-492f87ba_p0_requests.jsonl:41；analysis_step=8，snapshot_action=23。

```json
[
  {
    "field": "boundary",
    "kind": "subscript_load",
    "code_line": 5,
    "expression": "n['boundary']",
    "enclosing_scopes": [
      "If",
      "For",
      "FunctionDef"
    ]
  }
]
```

## m0r0-492f87ba · baseline · call_b6c533e8a516455e85a0c2c3

原件：runs/031-natural-aligned/baseline/m0r0-492f87ba_p0_requests.jsonl:59；analysis_step=13，snapshot_action=49。

```json
[
  {
    "field": "boundary",
    "kind": "subscript_load",
    "code_line": 5,
    "expression": "n['boundary']",
    "enclosing_scopes": [
      "If",
      "For"
    ]
  },
  {
    "field": "boundary",
    "kind": "subscript_load",
    "code_line": 5,
    "expression": "n['boundary']",
    "enclosing_scopes": [
      "If",
      "For"
    ]
  }
]
```

## tr87-cd924810 · baseline · call_f31490aa3a434bcb966b2b69

原件：runs/031-natural-aligned/baseline/tr87-cd924810_p0_requests.jsonl:3；analysis_step=1，snapshot_action=1。

```json
[
  {
    "field": "boundary",
    "kind": "subscript_load",
    "code_line": 5,
    "expression": "n['boundary']",
    "enclosing_scopes": [
      "For"
    ]
  }
]
```

## tr87-cd924810 · baseline · call_9644e62a92754081955ef848

原件：runs/031-natural-aligned/baseline/tr87-cd924810_p0_requests.jsonl:11；analysis_step=1，snapshot_action=1。

```json
[
  {
    "field": "boundary",
    "kind": "subscript_load",
    "code_line": 3,
    "expression": "n['boundary']",
    "enclosing_scopes": [
      "For"
    ]
  }
]
```

## tr87-cd924810 · baseline · call_bd646cd87eba4c13a596bb17

原件：runs/031-natural-aligned/baseline/tr87-cd924810_p0_requests.jsonl:13；analysis_step=1，snapshot_action=1。

```json
[
  {
    "field": "boundary",
    "kind": "subscript_load",
    "code_line": 11,
    "expression": "n['boundary']",
    "enclosing_scopes": [
      "FunctionDef"
    ]
  }
]
```

## tr87-cd924810 · baseline · call_abb5d316edd2491f9ad0863a

原件：runs/031-natural-aligned/baseline/tr87-cd924810_p0_requests.jsonl:25；analysis_step=5，snapshot_action=10。

```json
[
  {
    "field": "boundary",
    "kind": "subscript_load",
    "code_line": 8,
    "expression": "n['boundary']",
    "enclosing_scopes": [
      "comprehension",
      "If",
      "For",
      "FunctionDef"
    ]
  }
]
```

## tr87-cd924810 · baseline · call_f85da2ebc029449eb9a7c3c8

原件：runs/031-natural-aligned/baseline/tr87-cd924810_p0_requests.jsonl:27；analysis_step=6，snapshot_action=26。

```json
[
  {
    "field": "boundary",
    "kind": "subscript_load",
    "code_line": 8,
    "expression": "n['boundary']",
    "enclosing_scopes": [
      "comprehension",
      "If",
      "For",
      "FunctionDef"
    ]
  }
]
```

## tr87-cd924810 · baseline · call_4e24258c984441478a2e6140

原件：runs/031-natural-aligned/baseline/tr87-cd924810_p0_requests.jsonl:37；analysis_step=6，snapshot_action=26。

```json
[
  {
    "field": "boundary",
    "kind": "subscript_load",
    "code_line": 16,
    "expression": "n['boundary']",
    "enclosing_scopes": [
      "comprehension",
      "If",
      "For",
      "FunctionDef"
    ]
  }
]
```

## tr87-cd924810 · baseline · call_4669a6667c714fd5a815a8bb

原件：runs/031-natural-aligned/baseline/tr87-cd924810_p0_requests.jsonl:51；analysis_step=6，snapshot_action=26。

```json
[
  {
    "field": "boundary",
    "kind": "subscript_load",
    "code_line": 14,
    "expression": "n['boundary']",
    "enclosing_scopes": [
      "comprehension",
      "If",
      "For",
      "FunctionDef"
    ]
  }
]
```

## tr87-cd924810 · baseline · call_e9d12eec92714fabb6a6bcbd

原件：runs/031-natural-aligned/baseline/tr87-cd924810_p0_requests.jsonl:73；analysis_step=10，snapshot_action=65。

```json
[
  {
    "field": "boundary",
    "kind": "subscript_load",
    "code_line": 14,
    "expression": "n['boundary']",
    "enclosing_scopes": [
      "comprehension",
      "If",
      "For",
      "FunctionDef"
    ]
  }
]
```

## tr87-cd924810 · baseline · call_c146c0d685214b64ad97107e

原件：runs/031-natural-aligned/baseline/tr87-cd924810_p0_requests.jsonl:85；analysis_step=12，snapshot_action=93。

```json
[
  {
    "field": "boundary",
    "kind": "subscript_load",
    "code_line": 32,
    "expression": "n['boundary']",
    "enclosing_scopes": [
      "comprehension",
      "If",
      "For",
      "FunctionDef"
    ]
  }
]
```
