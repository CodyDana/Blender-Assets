// Copyright Epic Games, Inc. All Rights Reserved.

#include "NinjaFreeLookComponent.h"

#include "EnhancedInputComponent.h"
#include "GameFramework/Character.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "GameFramework/Controller.h"
#include "GameFramework/PlayerController.h"
#include "HAL/IConsoleManager.h"
#include "InputAction.h"

DEFINE_LOG_CATEGORY_STATIC(LogNinjaFreeLook, Log, All);

static TAutoConsoleVariable<int32> CVarNinjaFreeLookDebug(
	TEXT("ninja.freelook.debug"), 0, TEXT("Log the free-look anchor and how far the camera has swung from it."), ECVF_Default);

UNinjaFreeLookComponent::UNinjaFreeLookComponent()
{
	PrimaryComponentTick.bCanEverTick = true;
	// Before the movement component consumes the pending input, after the controller has added this frame's.
	PrimaryComponentTick.TickGroup = TG_PrePhysics;
}

ACharacter* UNinjaFreeLookComponent::GetCharacter() const
{
	return Cast<ACharacter>(GetOwner());
}

void UNinjaFreeLookComponent::BeginPlay()
{
	Super::BeginPlay();
	if (const ACharacter* Character = GetCharacter())
	{
		if (UCharacterMovementComponent* Movement = Character->GetCharacterMovement())
		{
			Movement->AddTickPrerequisiteComponent(this);
		}
	}
}

void UNinjaFreeLookComponent::UpdateInputBinding()
{
	const APawn* Pawn = Cast<APawn>(GetOwner());
	UInputComponent* Input = Pawn ? Pawn->InputComponent.Get() : nullptr;
	const APlayerController* PC = Pawn ? Cast<APlayerController>(Pawn->GetController()) : nullptr;
	if (!Input || !PC || !PC->IsLocalController() || !FreeLookAction)
	{
		BoundInputComponent.Reset();
		return;
	}
	if (BoundInputComponent.Get() == Input)
	{
		return;
	}
	BoundInputComponent = Input;
	if (UEnhancedInputComponent* Enhanced = Cast<UEnhancedInputComponent>(Input))
	{
		Enhanced->BindAction(FreeLookAction, ETriggerEvent::Started, this, &UNinjaFreeLookComponent::OnFreeLookPressed);
		Enhanced->BindAction(FreeLookAction, ETriggerEvent::Completed, this, &UNinjaFreeLookComponent::OnFreeLookReleased);
		Enhanced->BindAction(FreeLookAction, ETriggerEvent::Canceled, this, &UNinjaFreeLookComponent::OnFreeLookReleased);
	}
}

void UNinjaFreeLookComponent::OnFreeLookPressed()
{
	const ACharacter* Character = GetCharacter();
	AController* Controller = Character ? Character->GetController() : nullptr;
	if (!bEnabled || !Controller)
	{
		return;
	}
	bFreeLooking = true;
	bReturning = false;
	AnchorRotation = Controller->GetControlRotation();
	if (CVarNinjaFreeLookDebug.GetValueOnGameThread() != 0)
	{
		UE_LOG(LogNinjaFreeLook, Log, TEXT("%s: free look ON, anchor yaw %.0f"), *GetNameSafe(GetOwner()), AnchorRotation.Yaw);
	}
}

void UNinjaFreeLookComponent::OnFreeLookReleased()
{
	if (!bFreeLooking)
	{
		return;
	}
	bFreeLooking = false;
	const ACharacter* Character = GetCharacter();
	AController* Controller = Character ? Character->GetController() : nullptr;
	if (!Controller)
	{
		return;
	}
	if (ReturnTime <= 0.0f)
	{
		Controller->SetControlRotation(AnchorRotation);
	}
	else
	{
		bReturning = true;
		ReturnElapsed = 0.0f;
		ReturnFrom = Controller->GetControlRotation();
	}
	if (CVarNinjaFreeLookDebug.GetValueOnGameThread() != 0)
	{
		UE_LOG(LogNinjaFreeLook, Log, TEXT("%s: free look OFF, camera back to yaw %.0f"), *GetNameSafe(GetOwner()), AnchorRotation.Yaw);
	}
}

void UNinjaFreeLookComponent::TickComponent(float DeltaTime, ELevelTick TickType, FActorComponentTickFunction* ThisTickFunction)
{
	Super::TickComponent(DeltaTime, TickType, ThisTickFunction);
	ACharacter* Character = GetCharacter();
	if (!Character)
	{
		return;
	}
	// After the controller, so the mouse this frame is already in the control rotation and the pending movement vector.
	AController* Controller = Character->GetController();
	if (Controller != PrerequisiteController.Get())
	{
		if (AController* Old = PrerequisiteController.Get())
		{
			RemoveTickPrerequisiteActor(Old);
		}
		if (Controller)
		{
			AddTickPrerequisiteActor(Controller);
		}
		PrerequisiteController = Controller;
	}
	UpdateInputBinding();
	if (!Controller)
	{
		return;
	}

	if (bReturning)
	{
		ReturnElapsed += DeltaTime;
		const float Alpha = FMath::Clamp(ReturnElapsed / FMath::Max(ReturnTime, KINDA_SMALL_NUMBER), 0.0f, 1.0f);
		Controller->SetControlRotation(FMath::RInterpTo(ReturnFrom, AnchorRotation, Alpha, 1.0f));
		if (Alpha >= 1.0f)
		{
			Controller->SetControlRotation(AnchorRotation);
			bReturning = false;
		}
	}

	if (!bFreeLooking || !bEnabled)
	{
		return;
	}

	// How far the camera has swung since the key went down, clamped so you cannot wind round forever.
	float Swing = FMath::FindDeltaAngleDegrees(AnchorRotation.Yaw, Controller->GetControlRotation().Yaw);
	if (FMath::Abs(Swing) > MaxYaw)
	{
		const float Clamped = FMath::Sign(Swing) * MaxYaw;
		FRotator Limited = Controller->GetControlRotation();
		Limited.Yaw = AnchorRotation.Yaw + Clamped;
		Controller->SetControlRotation(Limited);
		Swing = Clamped;
	}

	// Movement input is camera-relative, so undoing the swing keeps W pushing along the heading the run started on.
	const FVector Pending = Character->ConsumeMovementInputVector();
	if (!Pending.IsNearlyZero())
	{
		const FVector Corrected = FRotator(0.0f, -Swing, 0.0f).RotateVector(Pending);
		Character->AddMovementInput(Corrected, 1.0f, /*bForce*/ false);
		if (CVarNinjaFreeLookDebug.GetValueOnGameThread() != 0)
		{
			UE_LOG(LogNinjaFreeLook, Log, TEXT("%s: swing %.0f deg, input (%.2f %.2f) -> (%.2f %.2f)"),
				*GetNameSafe(GetOwner()), Swing, Pending.X, Pending.Y, Corrected.X, Corrected.Y);
		}
	}
}
