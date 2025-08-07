#include <SPI.h>
#include <MFRC522.h>

#define SS_PIN 10
#define RST_PIN 9

MFRC522 mfrc522(SS_PIN, RST_PIN);

String command = "";
String dataToWrite = "";
bool waitingForCard = false;
String currentOperation = "";
int blocksToWrite = 1;
int blocksToRead = 15; // Maximum blocks to read

// Block configuration - using multiple sectors
const int BLOCKS_PER_SECTOR = 4;
const int DATA_BLOCKS_PER_SECTOR = 3; // Blocks 0, 1, 2 (block 3 is sector trailer)
const int MAX_SECTORS = 5; // Using first 5 sectors for data
const int BYTES_PER_BLOCK = 16;

void setup() {
  Serial.begin(9600);
  SPI.begin();
  mfrc522.PCD_Init();
  Serial.println("RFID Manager Ready - Multi-Block Support with Auto-Clear");
  Serial.println("Waiting for commands...");
}

void loop() {
  // Check for serial commands
  if (Serial.available() > 0) {
    String input = Serial.readStringUntil('\n');
    input.trim();
    
    if (input == "READ_MULTI") {
      currentOperation = "READ_MULTI";
      waitingForCard = true;
      Serial.println("Ready to read multiple blocks. Please place card near reader...");
    }
    else if (input.startsWith("WRITE_MULTI:")) {
      currentOperation = "WRITE_MULTI";
      blocksToWrite = input.substring(12).toInt();
      Serial.print("Ready to write ");
      Serial.print(blocksToWrite);
      Serial.println(" blocks. Send message to write...");
    }
    else if (input == "READ") {
      // Legacy single block read
      currentOperation = "READ";
      waitingForCard = true;
      Serial.println("Ready to read single block. Please place card near reader...");
    }
    else if (input == "WRITE") {
      // Legacy single block write
      currentOperation = "WRITE";
      blocksToWrite = 1;
      Serial.println("Ready to receive data. Send message to write...");
    }
    else if ((currentOperation == "WRITE_MULTI" || currentOperation == "WRITE") && !waitingForCard) {
      dataToWrite = input;
      waitingForCard = true;
      Serial.print("Ready to write. Message length: ");
      Serial.print(dataToWrite.length());
      Serial.println(" characters. Please place card near reader...");
    }
  }
  
  // Handle card operations
  if (waitingForCard && mfrc522.PICC_IsNewCardPresent() && mfrc522.PICC_ReadCardSerial()) {
    if (currentOperation == "READ" || currentOperation == "READ_MULTI") {
      if (currentOperation == "READ_MULTI") {
        readMultipleBlocks();
      } else {
        readSingleBlock();
      }
    }
    else if (currentOperation == "WRITE" || currentOperation == "WRITE_MULTI") {
      if (currentOperation == "WRITE_MULTI") {
        writeMultipleBlocks();
      } else {
        writeSingleBlock();
      }
    }
    
    waitingForCard = false;
    currentOperation = "";
    mfrc522.PICC_HaltA();
    mfrc522.PCD_StopCrypto1();
  }
}

void clearAllDataBlocks() {
  Serial.println("Clearing all data blocks...");
  
  MFRC522::MIFARE_Key key;
  for (byte i = 0; i < 6; i++) key.keyByte[i] = 0xFF;
  
  byte emptyBlock[16];
  for (byte i = 0; i < 16; i++) emptyBlock[i] = 0; // Fill with zeros
  
  int blocksCleared = 0;
  
  // Clear all data blocks in all sectors
  for (int sector = 1; sector < MAX_SECTORS; sector++) {
    for (int blockInSector = 0; blockInSector < DATA_BLOCKS_PER_SECTOR; blockInSector++) {
      byte block = sector * BLOCKS_PER_SECTOR + blockInSector;
      
      // Authenticate for this sector
      MFRC522::StatusCode status = mfrc522.PCD_Authenticate(
        MFRC522::PICC_CMD_MF_AUTH_KEY_A, block, &key, &(mfrc522.uid)
      );
      
      if (status != MFRC522::STATUS_OK) {
        Serial.print("Clear auth failed for block ");
        Serial.print(block);
        Serial.print(": ");
        Serial.println(mfrc522.GetStatusCodeName(status));
        continue;
      }
      
      status = mfrc522.MIFARE_Write(block, emptyBlock, 16);
      
      if (status == MFRC522::STATUS_OK) {
        blocksCleared++;
      } else {
        Serial.print("Clear failed for block ");
        Serial.print(block);
        Serial.print(": ");
        Serial.println(mfrc522.GetStatusCodeName(status));
      }
    }
  }
  
  Serial.print("Cleared ");
  Serial.print(blocksCleared);
  Serial.println(" data blocks");
}

void readSingleBlock() {
  byte block = 4;
  byte buffer[18];
  byte size = sizeof(buffer);

  MFRC522::MIFARE_Key key;
  for (byte i = 0; i < 6; i++) key.keyByte[i] = 0xFF;

  MFRC522::StatusCode status = mfrc522.PCD_Authenticate(
    MFRC522::PICC_CMD_MF_AUTH_KEY_A, block, &key, &(mfrc522.uid)
  );

  if (status != MFRC522::STATUS_OK) {
    Serial.print("Read failed: Authentication error - ");
    Serial.println(mfrc522.GetStatusCodeName(status));
    return;
  }

  status = mfrc522.MIFARE_Read(block, buffer, &size);

  if (status == MFRC522::STATUS_OK) {
    Serial.print("DATA:");
    for (byte i = 0; i < 16; i++) {
      if (buffer[i] != 0) {
        Serial.write(buffer[i]);
      }
    }
    Serial.println();
    Serial.println("Read successful!");
  } else {
    Serial.print("Read failed: ");
    Serial.println(mfrc522.GetStatusCodeName(status));
  }
}

void readMultipleBlocks() {
  String fullData = "";
  MFRC522::MIFARE_Key key;
  for (byte i = 0; i < 6; i++) key.keyByte[i] = 0xFF;
  
  Serial.println("Reading multiple blocks...");
  
  // Read from multiple sectors and blocks
  for (int sector = 1; sector < MAX_SECTORS; sector++) {
    for (int blockInSector = 0; blockInSector < DATA_BLOCKS_PER_SECTOR; blockInSector++) {
      byte block = sector * BLOCKS_PER_SECTOR + blockInSector;
      byte buffer[18];
      byte size = sizeof(buffer);
      
      // Authenticate for this sector
      MFRC522::StatusCode status = mfrc522.PCD_Authenticate(
        MFRC522::PICC_CMD_MF_AUTH_KEY_A, block, &key, &(mfrc522.uid)
      );
      
      if (status != MFRC522::STATUS_OK) {
        Serial.print("Auth failed for block ");
        Serial.print(block);
        Serial.print(": ");
        Serial.println(mfrc522.GetStatusCodeName(status));
        continue;
      }
      
      status = mfrc522.MIFARE_Read(block, buffer, &size);
      
      if (status == MFRC522::STATUS_OK) {
        // Check if block contains data (not all zeros)
        bool hasData = false;
        for (byte i = 0; i < 16; i++) {
          if (buffer[i] != 0) {
            hasData = true;
            break;
          }
        }
        
        if (hasData) {
          for (byte i = 0; i < 16; i++) {
            if (buffer[i] != 0) {
              fullData += (char)buffer[i];
            }
          }
        } else {
          // If we hit an empty block, we've reached the end of data
          goto read_complete;
        }
      } else {
        Serial.print("Read failed for block ");
        Serial.print(block);
        Serial.print(": ");
        Serial.println(mfrc522.GetStatusCodeName(status));
      }
    }
  }
  
  read_complete:
  if (fullData.length() > 0) {
    Serial.print("DATA:");
    Serial.println(fullData);
    Serial.print("Read successful! Total characters: ");
    Serial.println(fullData.length());
  } else {
    Serial.println("Read failed: No data found");
  }
}

void writeSingleBlock() {
  // Clear the single block first
  Serial.println("Clearing block 4...");
  
  byte block = 4;
  byte emptyBlock[16];
  for (byte i = 0; i < 16; i++) emptyBlock[i] = 0;
  
  MFRC522::MIFARE_Key key;
  for (byte i = 0; i < 6; i++) key.keyByte[i] = 0xFF;

  // Clear the block first
  MFRC522::StatusCode status = mfrc522.PCD_Authenticate(
    MFRC522::PICC_CMD_MF_AUTH_KEY_A, block, &key, &(mfrc522.uid)
  );

  if (status == MFRC522::STATUS_OK) {
    mfrc522.MIFARE_Write(block, emptyBlock, 16);
    Serial.println("Block cleared");
  }

  // Now write the new data
  byte dataBlock[16];
  for (byte i = 0; i < 16; i++) {
    dataBlock[i] = (i < dataToWrite.length()) ? dataToWrite[i] : 0;
  }

  status = mfrc522.PCD_Authenticate(
    MFRC522::PICC_CMD_MF_AUTH_KEY_A, block, &key, &(mfrc522.uid)
  );

  if (status != MFRC522::STATUS_OK) {
    Serial.print("Write failed: Authentication error - ");
    Serial.println(mfrc522.GetStatusCodeName(status));
    return;
  }

  status = mfrc522.MIFARE_Write(block, dataBlock, 16);

  if (status == MFRC522::STATUS_OK) {
    Serial.println("Write successful!");
  } else {
    Serial.print("Write failed: ");
    Serial.println(mfrc522.GetStatusCodeName(status));
  }
  
  dataToWrite = "";
}

void writeMultipleBlocks() {
  // First, clear all data blocks
  clearAllDataBlocks();
  
  MFRC522::MIFARE_Key key;
  for (byte i = 0; i < 6; i++) key.keyByte[i] = 0xFF;
  
  Serial.print("Writing ");
  Serial.print(dataToWrite.length());
  Serial.println(" characters to multiple blocks...");
  
  int dataIndex = 0;
  int blocksWritten = 0;
  
  // Write to multiple sectors and blocks
  for (int sector = 1; sector < MAX_SECTORS && dataIndex < dataToWrite.length(); sector++) {
    for (int blockInSector = 0; blockInSector < DATA_BLOCKS_PER_SECTOR && dataIndex < dataToWrite.length(); blockInSector++) {
      byte block = sector * BLOCKS_PER_SECTOR + blockInSector;
      byte dataBlock[16];
      
      // Prepare data block
      for (byte i = 0; i < 16; i++) {
        if (dataIndex < dataToWrite.length()) {
          dataBlock[i] = dataToWrite[dataIndex++];
        } else {
          dataBlock[i] = 0; // Pad with zeros
        }
      }
      
      // Authenticate for this sector
      MFRC522::StatusCode status = mfrc522.PCD_Authenticate(
        MFRC522::PICC_CMD_MF_AUTH_KEY_A, block, &key, &(mfrc522.uid)
      );
      
      if (status != MFRC522::STATUS_OK) {
        Serial.print("Auth failed for block ");
        Serial.print(block);
        Serial.print(": ");
        Serial.println(mfrc522.GetStatusCodeName(status));
        continue;
      }
      
      status = mfrc522.MIFARE_Write(block, dataBlock, 16);
      
      if (status == MFRC522::STATUS_OK) {
        blocksWritten++;
        Serial.print("Block ");
        Serial.print(block);
        Serial.println(" written successfully");
      } else {
        Serial.print("Write failed for block ");
        Serial.print(block);
        Serial.print(": ");
        Serial.println(mfrc522.GetStatusCodeName(status));
      }
    }
  }
  
  if (blocksWritten > 0) {
    Serial.print("Write successful! ");
    Serial.print(blocksWritten);
    Serial.print(" blocks written, ");
    Serial.print(dataToWrite.length());
    Serial.println(" characters total.");
  } else {
    Serial.println("Write failed: No blocks written");
  }
  
  dataToWrite = "";
}
